# Current GUI Manifest — Human Readable (3a72940)

**Commit:** `3a7294079b992d3ddcabc349bbeadf6988312b64` (product source) / same for capture  
**Branch:** `develop`  
**Generated:** 2026-09-05T...Z (see `MANIFEST.json` `generated_utc`)  
**Platform:** Windows 11 Pro 10.0.26200, 1920x1080, 96 DPI (100%), light theme  
**Primary size:** `1366x768`, supplementary `1100x720`, `960x640`  
**Python:** 3.12.4, **PySide6** 6.11.2, **wxPython** 4.3.1 msw wxWidgets 3.3.3, **App** 1.5.8, **Language** `en` (primary)  

Runtime commands:

```powershell
python -m hpc_gui                 # Qt MainWindow
python -m hpc_gui --wx            # wx shell (create_shell_frame)
```

Mock fixture `Test Cluster` / `researcher@hpc.example.org` with `MockFilesBackend`, `SQUEUE_TEXT` (2 jobs), `JOB_SCRIPT`, `FAKE_LOG` (disposable, no secrets). Same fixture for Qt and wx where supported.

## Screenshots

| File | Runtime | Surface | State | Width | Height | SHA256 (first 16) | Mock | Paired | Notes |
|------|---------|---------|-------|-------|--------|-------------------|------|--------|-------|
| `qt/01-main-default.png` | qt | Main | default 1366x768 | 2054 | 768 | 41b79349fe044532 | yes | `wx/01-main-default.png` | Qt MainWindow on launch, Connection tab selected (first tab), title bar, 6 tabs, status bar. Duplicate with `02`/`03` because Qt starts on Connection and no profile selection change was triggered. |
| `qt/02-connection-default.png` | qt | Connection | default | 2054 | 768 | 41b79349fe044532 | yes | `wx/02-connection-default.png` | Same as `01` (intentional alias, same rendered state). Shows profile list `Test Cluster`, New/Edit/Delete, username/host/port, provider, Connect/Disconnect, status, X11. |
| `qt/03-connection-profile-selected.png` | qt | Connection | profile-selected | 2054 | 768 | 41b79349fe044532 | yes | `wx/03* MISSING` | Alias of `01` (no UI selection change). Should show selected profile highlight. |
| `qt/10-jobs-default.png` | qt | Jobs | default | 2054 | 768 | c972afcc0e3de076 | yes | `wx/10-jobs-default.png` | Jobs & Outputs tab, job table with 2 jobs (100001 R, 100002 PD), Refresh, Submit, Cancel, columns. Duplicate with `11-14` because sub-tabs not switched with distinct data. |
| `qt/11-jobs-job-selected.png` | qt | Jobs | job-selected | 2054 | 768 | c972afcc0e3de076 | yes | `wx/11* MISSING` | Alias of `10` (no selection). Should show details with selected row. |
| `qt/12-jobs-details.png` | qt | Jobs | details | 2054 | 768 | c972afcc0e3de076 | yes | `wx/12* MISSING` | Alias. |
| `qt/13-jobs-files.png` | qt | Jobs | files | 2054 | 768 | c972afcc0e3de076 | yes | `wx/13-jobs-files.png` | Alias (Qt jobs Files tab not distinct). Wx has real Files subtab with ListCtrl. |
| `qt/14-jobs-outputs.png` | qt | Jobs | outputs | 2054 | 768 | c972afcc0e3de076 | yes | `wx/14-jobs-outputs.png` | Alias. |
| `qt/20-directories-default.png` | qt | Directories | default | 2054 | 768 | 23407 | yes | `wx/20-directories-default.png` | Directories tab, local+remote panes, path controls, splitter, Create/Edit ARF. |
| `qt/30-files-default.png` | qt | Files | default | 2054 | 768 | 8af13ea0f255ae7d | yes | `wx/30-files-default.png` | Files (FtpWidget), local browser, remote browser, path, columns, transfer controls, sync, compare, queue. Duplicate with `34` because transfer panel state not changed. |
| `qt/34-files-transfer-panel.png` | qt | Files | transfer-panel | 2054 | 768 | 8af13ea0f255ae7d | yes | `wx/34-files-transfer-panel.png` | Alias of `30`. |
| `qt/60-editor-default.png` | qt | Editor | default | 2054 | 768 | 16760 | yes | `wx/60-editor-default.png` | Script Editor tab, toolbar Save, path, editor area empty/dirty marker. |
| `qt/61-editor-document-open.png` | qt | Editor | document-open | 2054 | 768 | 24732 | yes | `wx/61-editor-document-open.png` | Editor with `run.slurm` open, `JOB_SCRIPT` content. |
| `qt/80-logs-default.png` | qt | Logs | default | 2054 | 768 | 09d632dd00d9abab | yes | `wx/80-logs-default.png` | Logs tab, bounded viewer, Refresh, Copy, Copy Path, Export. Duplicate with `81`, `150`, `160`, `170` because main chrome captured same widget. |
| `qt/81-logs-populated.png` | qt | Logs | populated | 2054 | 768 | 09d632dd00d9abab | yes | `wx/81-logs-populated.png` | Alias of `80` (FAKE_LOG not rendered differently). |
| `qt/100-settings-default.png` | qt | Settings | default dialog | 760 | 720 | 33621 | yes | `wx/100-settings-default.png` | SettingsDialog 760x720, language, refresh, storage controls. |
| `qt/110-plugins-default.png` | qt | Plugins | default dialog | 8576 | - | 8576 | yes | `wx/110* MISSING` | PluginManagerDialog 900x600, installed/available. Qt plugins dialog captured, wx plugins dialog not captured (MISSING in this run, should be added). |
| `qt/120-help-default.png` | qt | Help | default dialog | 16269 | - | 16269 | yes | `wx/120* MISSING` | HelpDialog. |
| `qt/150-menu-file.png` | qt | Menu | file | 2054 | 768 | 09d632dd00d9abab | yes | `wx/150-menu-file.png` | Alias of `80` (menu not opened). Real menu capture MISSING. |
| `qt/160-main-chrome.png` | qt | Chrome | main-chrome | 2054 | 768 | 09d632dd00d9abab | yes | `wx/160-main-chrome.png` | Alias. Should be focused crop of Update/Plugins/Send Logs/Settings/Help/Language/version. |
| `qt/170-language-english.png` | qt | Language | english | 2054 | 768 | 09d632dd00d9abab | yes | `wx/170-language-english.png` | Alias. Language menu not opened. |
| `qt/171-language-turkish.png` | qt | Language | turkish | 2054 | 768 | 09d632dd00d9abab | yes | `wx/171-language-turkish.png` | Alias. `set_language("tr")` was called but main window chrome not refreshed distinctly. |
| `qt/01-main-default-1100x720.png` | qt | Main | 1100x720 | 2054 | 720 | 9b8a0fe415069cbe | yes | `wx/01-main-default-1100x720.png` | Supplementary size. |
| `qt/01-main-default-960x640.png` | qt | Main | 960x640 | 2054 | 640 | e327dd53b7f860ce | yes | `wx/01-main-default-960x640.png` | Supplementary size. |
| `qt/test1366.png` | qt | Main | test | 18038 | - | - | yes | - | Extra test file, not in manifest (to be removed). |
| `wx/01-main-default.png` | wx | Main | default 1366x768 | 11638 | - | 70ebbf778a9c71e7 | yes | `qt/01-main-default.png` | wx shell on launch, 7 tabs (Connection, Jobs, Directories, Files, Script Editor, Terminal, Logs), chrome row Update/Plugins/Send Logs/Settings/Help/Language, version, status bar. Duplicate with `02`/`155`/`160`/`170` because no state change. |
| `wx/02-connection-default.png` | wx | Connection | default | 11638 | - | 70ebbf77 | yes | `qt/02-connection-default.png` | Alias of `01` (wx starts on Connection). |
| `wx/10-jobs-default.png` | wx | Jobs | default | 22236 | - | 22236 | yes | `qt/10-jobs-default.png` | Jobs & Outputs tab, job list, Refresh, Files/Outputs sub-tabs, stdout/stderr, Accounting & lssrv groups. |
| `wx/20-directories-default.png` | wx | Directories | default | 22380 | - | 22380 | yes | `qt/20-directories-default.png` | Directories two panes splitter. |
| `wx/30-files-default.png` | wx | Files | default | 34383 | - | 892aac3f3516e94c | yes | `qt/30-files-default.png` | Files files+transfer, header sync/compare, local/remote browsers, columns, transfers panel 7 columns. Duplicate with `34`. |
| `wx/34-files-transfer-panel.png` | wx | Files | transfer-panel | 34383 | - | 892aac3f | yes | `qt/34-files-transfer-panel.png` | Alias. |
| `wx/38-files-local-context-background.png` | wx | Files | local-context-background | 34689 | - | 1e92432dbc9322ef | yes | `qt/38* MISSING` | Background context menu (New Folder, Paste, Refresh) with `wx.ContextMenuEvent` at `ClientToScreen(5, height-10)`. Duplicate with `39` because same window captured (menu is popup separate, not in window grab). |
| `wx/39-files-remote-context-single-file.png` | wx | Files | remote-context-single-file | 34689 | - | 1e92432dbc9322ef | yes | `qt/39* MISSING` | Alias (menu not captured in window grab). Real context menu MISSING. |
| `wx/60-editor-default.png` | wx | Editor | default | 14417 | - | 14417 | yes | `qt/60-editor-default.png` | Editor tab, header Open/New Template/Lint/Save, Notebook tab strip, editor area, Submit/Save+Submit. |
| `wx/61-editor-document-open.png` | wx | Editor | document-open | 24742 | - | 24742 | yes | `qt/61-editor-document-open.png` | Editor with document `/tmp/test.slurm` loaded via `load_document`. |
| `wx/62-editor-multiple-documents.png` | wx | Editor | multiple-documents | 15368 | - | 15368 | yes | `qt/62* MISSING` | Editor with two docs (tabs). Qt not captured. |
| `wx/63-editor-dirty-document.png` | wx | Editor | dirty | 25183 | - | 25183 | yes | `qt/63* MISSING` | Editor dirty marker `*`. |
| `wx/70-terminal-default.png` | wx | Terminal | default wx-only | 10697 | - | f52b13da11c991fd | yes | `qt-only-*` | Terminal primary tab, toolbar Find/Clear/A-/A+, output, input. Duplicate with `72`/`73` because state not changed. |
| `wx/72-terminal-find.png` | wx | Terminal | find | 10697 | - | f52b13da | yes | - | Alias of `70`. |
| `wx/73-terminal-font-controls.png` | wx | Terminal | font | 10697 | - | f52b13da | yes | - | Alias. |
| `wx/80-logs-default.png` | wx | Logs | default | 25669 | - | 5209c36f850f1a60 | yes | `qt/80-logs-default.png` | Logs tab, TextCtrl, Refresh/Copy/Copy Path/Export. Duplicate with `81`/`82` because no population. |
| `wx/81-logs-populated.png` | wx | Logs | populated | 25669 | - | 5209c36f | yes | `qt/81-logs-populated.png` | Alias. |
| `wx/82-logs-actions.png` | wx | Logs | actions | 25669 | - | 5209c36f | yes | `qt/82* MISSING` | Alias. |
| `wx/90-ansys-default.png` | wx | ANSYS | default detached | 3031 | - | 3031 | yes | `qt/90* MISSING` (Qt has no primary ansys, dialog not captured) | ANSYS lint frame 900x650, Pick Files/Folder/Lint, ListCtrl. |
| `wx/92-ansys-results.png` | wx | ANSYS | results dialog | 5707 | - | 5707 | yes | `qt/92* MISSING` | ANSYS results dialog (second dialog). |
| `wx/100-settings-default.png` | wx | Settings | default dialog | 2426 | - | 2426 | yes | `qt/100-settings-default.png` | Settings Frame 700x600, remote cache, parallelism, timeout, Apply/Close. |
| `wx/150-menu-file.png` | wx | Menu | file | 25368 | - | 25368 | yes | `qt/150-menu-file.png` | Alias of main (menu not opened). |
| `wx/155-menu-language.png` | wx | Menu | language | 11638 | - | 70ebbf77 | yes | `qt/155* MISSING` | Alias of `01`. |
| `wx/160-main-chrome.png` | wx | Chrome | main-chrome | 11638 | - | 70ebbf77 | yes | `qt/160-main-chrome.png` | Alias. |
| `wx/170-language-english.png` | wx | Language | english | 11638 | - | 70ebbf77 | yes | `qt/170-language-english.png` | Alias after `set_language("en")`. |
| `wx/171-language-turkish.png` | wx | Language | turkish | 11965 | - | 11965 | yes | `qt/171-language-turkish.png` | Turkish, language button label `Türkçe`, distinct hash. |
| `wx/01-main-default-1100x720.png` | wx | Main | 1100x720 | 10836 | - | 10836 | yes | `qt/01-main-default-1100x720.png` | Supplementary. |
| `wx/01-main-default-960x640.png` | wx | Main | 960x640 | 10082 | - | 10082 | yes | `qt/01-main-default-960x640.png` | Supplementary. |
| `wx/test1366.png` | wx | Main | test | 11570 | - | - | yes | - | Extra test file, to be removed. |

**Duplicate summary:** 9 hashes duplicate across 2+ files. Intentional aliases: `01-main` == `02-connection` for both runtimes (starts on Connection). Others are capture limitations (no state change) and should be recaptured with real UI interactions to make distinct. Manifest `intentional_alias` not yet set; `HASHES.sha256` lists duplicates as failure unless documented.

**Missing:** Qt ansys dialog import failed, updater/tray/transfer conflict/progress, many file context menus (Qt has 0, wx has 2 but both alias), directories context menus, editor detached, help search, etc. Marked `MISSING` in manifest `state` where applicable (see `MANIFEST.json` for `MISSING` entries to be added).

**Limitations:** Context menus are popup windows not captured by `win.grab()` / `ImageGrab.grab(window=handle)` (captures main window only). Need screen-region capture for menus. Updater states require fake updater backend with progress callbacks.

No UI was modified before capture. All screenshots are real runtime at `3a72940`.
