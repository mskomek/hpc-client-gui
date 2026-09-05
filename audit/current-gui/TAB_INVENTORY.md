# Tab Inventory — Qt vs wx (3a72940)

**Source:** `src/hpc_gui/ui/main_window.py:138-157` (Qt), `src/hpc_gui/wx_shell.py:125-590` (wx) + runtime screenshots `01-main-default.png` at 1366x768.

| # | Qt Tab Order | Qt Title | Qt Icon | Qt Initial Selected | Qt Content | wx Tab Order | wx Title | wx Icon | wx Initial Selected | wx Content | Embedded vs Detached | Notes | Screenshot |
|---|--------------|----------|---------|---------------------|------------|--------------|----------|---------|---------------------|------------|----------------------|-------|------------|
| 0 | 0 | `tabs.login` / "Connection" / "Test Cluster" | none | **yes** (Qt starts on Connection) | `LoginWidget` profile list, Add/Edit/Delete, username/host/port, provider, Connect/Disconnect, status, X11, terminal embedded region | 0 | `tabs.login` / "Connection" | none (flag bitmap on language button, not tab) | **yes** (wx starts on Connection, `notebook.SetSelection(0)`) | `build_connection_panel` (same) | embedded (both) | Same order, same content | `qt/01-main-default.png` / `wx/01-main-default.png` (duplicate hash intentional) |
| 1 | 1 | `tabs.jobs_outputs` / "Jobs & Outputs" | none | no | `JobsOutputsWidget` job table (2 jobs), Refresh, Submit, Cancel, details, Files/Outputs subtabs, stdout/stderr, follow | 1 | `tabs.jobs_outputs` / "Jobs & Outputs" | none | no | `build_jobs_panel` notebook with Details/Files/Outputs, job list, Refresh/Open Output/Pause/Auto-scroll/Cancel, Accounting & lssrv groups, Files ListCtrl via `list_job_files`, Outputs stdout/stderr via `read_output` | embedded (both) | wx adds Accounting & lssrv groups explicitly | `qt/10-jobs-default.png` / `wx/10-jobs-default.png` |
| 2 | 2 | `tabs.directories` / "Directories" | none | no | `DirectoriesWidget` two panes splitter, path titles, Create/Edit ARF, local/remote | 2 | `tabs.directories` / "Directories" | none | no | `build_directories_panel` two panes splitter | embedded | Same | `qt/20-directories-default.png` / `wx/20-directories-default.png` |
| 3 | 3 | `tabs.ftp` / "Files" | none | no | `FtpWidget` local browser, remote browser, path, columns, transfer controls, sync, compare, queue | 3 | `tabs.ftp` / "Files" | none | no | `build_local_files_panel` + `build_remote_files_panel` + `build_transfers_panel` in `SplitterWindow`, header `transfer_type` Choice, `effective_label`, `sync_cb`, `compare_btn`, Upload/Download | embedded | wx header row more explicit (WrapSizer) | `qt/30-files-default.png` / `wx/30-files-default.png` |
| 4 | 4 | `tabs.editor` / "Script Editor" | none | no | `EditorWidget` path, Open, New from Template..., Lint, Save, editor area, Submit/Save+Submit, dirty `*` | 4 | `tabs.editor` / "Script Editor" | none | no | `build_editor_panel` header `remote_label` + `remote_path` + `Open`/`New from Template`/`Lint`/`Save`, Notebook tab strip `dirty *`, `editor` TextCtrl, Submit/Run, status | embedded | wx tab strip always visible (even single doc) | `qt/60-editor-default.png` / `wx/60-editor-default.png` |
| 5 | - | - | - | - | - | 5 | `help.section_terminal` / "Terminal" | none | no | `build_terminal_panel` toolbar Find/Clear/A-/A+, output TextCtrl, input | embedded (wx-only) | **Intentional deviation** Qt has no primary Terminal tab; Qt terminal is embedded inside Connection (if any) | `wx/70-terminal-default.png` / `qt-only-*` |
| 6 | 5 | `tabs.logs` / "Logs" | none | no | `LogsWidget` title, TextCtrl, Refresh, Copy, Copy Path, Export Diagnostics | 6 | `tabs.logs` / "Logs" | none | no | `build_logs_panel` title, TextCtrl, Copy/Copy Path/Export/Refresh, bounded 5000, redaction | embedded | Same | `qt/80-logs-default.png` / `wx/80-logs-default.png` |

**Qt tab count:** 6
**wx tab count:** 7 (6 same + Terminal)

**Initial selected tab:** Both `0` (Connection) — verified via `win.tabs.currentIndex()` / `notebook.GetSelection()` == 0 and `01-main-default.png` shows Connection content.

**Embedded vs detached semantics:**

- All primary tabs are **embedded** in `QTabWidget` / `wx.Notebook` with `SplitterWindow` where needed. No launcher-only pages. No unexpected detached frames during normal tab selection (verified via `test_wx_layout_resize.py` 400 resizes, `layout_exceptions 0`).
- Detached windows exist only for secondary actions: Editor `New Window` (`WxEditorWindowManager` standalone `wx.Frame`), Jobs `Open Output` detached (`show_job_output`), ANSYS (`build_ansys_frame`), Settings/Plugins/Help dialogs. These are intentional detached.

**Visible title:** `HPC Client GUI 1.5.8` (both, `frame.GetTitle()` / `win.windowTitle()`)

**Icon:** Qt uses `build/macos/hpc-client-gui.icns` / `build/windows/hpc-client-gui.ico` if present; wx uses no tab icons, only flag bitmap on language button.

**Functional content:** See `CONTROL_INVENTORY.md` for per-tab controls.

**Screenshots:** `01-main-default.png` for main, `02-connection-default.png`, `10-jobs-default.png`, `20-directories-default.png`, `30-files-default.png`, `60-editor-default.png`, `70-terminal-default.png` (wx-only), `80-logs-default.png`, plus supplementary `01-main-default-1100x720.png`, `01-main-default-960x640.png`.
