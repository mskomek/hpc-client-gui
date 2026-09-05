# Differences Preview — Qt vs wx (factual, no judgment) — 3a72940

This is a **factual inventory** of visible differences between the current Qt reference and the current wx candidate, as seen in `audit/current-gui/qt/` vs `wx/` at 1366x768. No redesign decisions yet.

## Tab level

- Qt has 6 primary tabs: Connection, Jobs & Outputs, Directories, Files, Script Editor, Logs.
- wx has 7 primary tabs: same 6 plus **Terminal** as primary tab 5 (before Logs). `help.section_terminal`.
- **Fact:** Qt has no primary-tab Terminal; Qt terminal (if any) is embedded inside Connection. Wx Terminal is standalone primary tab with toolbar Find/Clear/A-/A+.

## Header / Chrome

- Both have top chrome row with `Update`, `Plugins`, `Send Logs`, `Settings`, `Help`, `Language` (flag), `version`, `HPC Client GUI 1.5.8`.
- Qt header is via `QMainWindow` menu bar + header widget; wx header is `wx.BoxSizer` `chrome_sizer` with `version_label` + 5 buttons + `language_button` (bitmap flag). Order same.
- Wx `language_button` shows flag bitmap via `wx.svg` (18x12) or solid color fallback; Qt shows flag via icons.
- Qt window decorations include native title bar; wx same.

## Connection

- Qt profile list is `QListWidget`; wx is `ListCtrl`/`ListBox`.
- Qt `Add Connection` enabled; wx `Add Connection` visible but disabled until callback is supplied (test seam).
- Qt may embed terminal inside Connection; wx keeps Terminal separate.

## Jobs & Outputs

- Qt has `JobsOutputsWidget` with job table + details + Files/Outputs subtabs.
- wx has same 3 sub-tabs but with explicit `Accounting & Job Details` group (`Refresh sacct`, `job id`, `Show job details`) and `Cluster Servers (lssrv)` group in Details page. Qt has similar but not in same tab location.
- Both have `Refresh`, `Submit`, `Cancel`, `Open Output`, `Pause Live Follow`, `Auto-scroll`.
- Wx `job_files` ListCtrl has 3 columns `dirs.col_name`, `dirs.col_size`, `jobs_outputs.file`; Qt similar.
- Wx `outputs_stdout`/`stderr` are separate `TextCtrl` in `SplitterWindow`; Qt similar.

## Directories

- Both have two panes splitter with `Create/Edit ARF Slurm` button. Wx uses `SplitterWindow` with `SetMinimumPaneSize(220)`, Qt uses similar.

## Files

- Both have header row: `Transfer type` Choice (`Auto`/`Binary`/`Ascii`) + `Effective` label, `Synchronized browsing` CheckBox, `Compare directories` Button, `Upload Selected`/`Download Selected` Buttons.
- Wx header uses `WrapSizer` so narrow windows wrap (Qt may not wrap).
- Qt `Sync`/`Compare` may be disabled until connected; wx leaves them enabled for test seam (guard inside handler).
- Both have local/remote browsers with 4 columns, filter tabs, and transfers panel with 7 columns and Queue/Failed/Completed tabs + Stop/Cancel/Clear row.
- Wx transfers panel is `build_transfers_panel` in `SplitterWindow` with `SetSashGravity(0.7)`; Qt similar.

## Editor

- Both have header: remote path field + `Open`, `New from Template...`, `Lint`, `Save`, editor area, `Submit`/`Save+Submit`.
- Qt document tabs are `QTabWidget` movable/closable; wx document tabs are `wx.Notebook` `doc_tabs` **always** visible (even single doc) with dirty `*`, duplicate suppression, reorder via drag. Qt may hide tab strip if single doc (older), wx always shows.
- Wx header path field has `SetMinSize(300,-1)` to ensure usable width in WrapSizer; Qt similar.

## Terminal

- Qt: no primary tab, terminal inside Connection if present, with Find/Clear/font via `TerminalWidget`.
- wx: primary tab `Terminal` with toolbar `Find` TextCtrl + `Find` Button, `Clear`, `A-`, `A+`, bounded 5000, `EVT_CHAR` PTY, `TextCtrl` with custom handling.

## Logs

- Both have title, `TextCtrl` `TE_MULTILINE|READONLY|HSCROLL`, and four buttons `Refresh`, `Copy`, `Copy Path`, `Export Diagnostics` in same order. Wx `Export` uses `DirDialog` + `Thread` → `bundle` → `MessageBox`; Qt similar with `QThread`.
- Both show `FAKE_LOG` with redaction.

## ANSYS

- Qt: `AnsysLintResultsDialog` (QDialog) with Pick Files/Folder/Lint, grouped severity, detail pane (Why/Confidence/Fix), Copy/Open docs, summary.
- wx: `build_ansys_frame` (wx.Frame 900x650) with same: Pick Files/Pick Folder/Lint → `WxAnsysModel` → grouped `ListCtrl` + severity + detail, `Copy diagnostic`/`Copy suggestion`/`Open documentation` (allowlist `is_allowed_external_url`), EN/TR i18n, 200 cap. Qt has no primary-tab ansys; wx is detached frame. `90-ansys-default.png` vs Qt `MISSING` (import failed).

## Settings

- Qt `SettingsDialog` 760x720 with language, refresh, storage, etc.
- wx `build_settings_panel` 700x600 Frame with `remote_directory_cache` CheckBox, `transfer_checksum` CheckBox, `transfer_parallelism` SpinCtrl 1-16, `ssh_timeout` 0-300, Apply/Close, `Thread` worker, `closed` guard, i18n. Qt has more controls (scroll lower) vs wx shows 4 main controls; lower scroll area not captured (MISSING).

## Plugins

- Qt `PluginManagerDialog` 900x600 with Online/Cached/Offline, allowlist, card/detail/capability.
- wx `show_plugins` via `wx_plugins_view` with similar but layout differs: Qt cards vs wx ListCtrl. `110-plugins-default.png` captured for both but wx detailed list not captured (MISSING).

## Help

- Both have `HelpDialog` searchable, Command Palette `Ctrl+Shift+P`, quick tour. Captured `120-help-default.png` for both.

## Menus

- Both have Help + Language top-level menus only (no File/Edit/View/Tools). Qt and wx Language menu has `English`/`Turkish` radio with flag. Wx also has chrome `language_button` popup menu. Context menus for Files/Jobs/Editor exist but were captured as main window only (menu popup not in window grab) — MISSING.

## Language

- Both support EN/TR via `set_language`. Main shell captured in both: `170-language-english.png` (EN) and `171-language-turkish.png` (TR). Wx Turkish screenshot `wx/171-...` has distinct hash `11965` vs English `11638` (label `Türkçe`), Qt Turkish is alias of English (no distinct capture because `set_language` not flushed before grab). Need to fix Qt Turkish capture.

## Empty/Loading/Error

- `180-empty-jobs.png` etc not captured (MISSING). Would require triggering empty job list via mock with 0 jobs.

## Disabled states

- Qt `Add Connection` enabled; wx `Add Connection` disabled until callback (visible disabled). Editor `Open`/`New Template`/`Lint` disabled in wx until callback, enabled in Qt. Documented in `CONTROL_INVENTORY.md` `enabled` columns.

## Summary

Wx is close to Qt control-for-control for primary tabs; remaining differences are:

- Terminal placement (wx primary vs Qt embedded)
- Jobs extra Accounting/lssrv groups in wx
- Editor tab strip always vs Qt conditional
- Files header WrapSizer vs Qt fixed
- Settings lower scroll not captured
- Context menus/Updater progress/Tray not captured in this run (need screen-region capture)
