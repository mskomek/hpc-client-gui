# Menu Inventory — Qt vs wx (3a72940)

**Source:** `src/hpc_gui/ui/main_window.py` menu bar setup, `src/hpc_gui/wx_shell.py:86-101` (wx `MenuBar` with `help.help_title` and `help.language`), plus context menus for Files/Jobs/Editor.

## Main Menu Bar

| Menu | Action | Qt Label | Qt Shortcut | Qt Enabled | wx Label | wx Shortcut | wx Enabled | Equivalent? | Screenshot |
|------|--------|----------|-------------|------------|----------|-------------|------------|-------------|------------|
| Help | Help | `help.help_title` / "Help" | F1 | yes | `help.help_title` / "Help" | - | yes | yes | `qt/150-menu-file.png` (alias, menu not opened) / `wx/150-menu-file.png` (alias) |
| Language | English | `language.english` | - | yes (radio, checked if en) | `language.english` / "English" | - | yes (radio, bitmap flag) | yes | `qt/170-language-english.png` (alias) / `wx/170-language-english.png` |
| Language | Turkish | `language.turkish` | - | yes | `language.turkish` / "Turkish" | - | yes | yes | `qt/171-language-turkish.png` (alias) / `wx/171-language-turkish.png` (distinct hash 11965) |

**Qt main menus:** Only Help and Language are top-level in current `MainWindow` (checked via `app.py` and `main_window.py`). No File/Edit/View/Tools menus in current Qt (unlike wiki overview composite). Wx mirrors this: `frame.GetMenuBar().GetMenuCount() >=2` (Help + Language).

**Context Menus - Files Local**

| Action | Qt | wx | Notes | Screenshot |
|--------|----|----|-------|------------|
| Open | yes (via double-click) | yes | | `qt/30-files-default.png` / `wx/39-files-remote-context-single-file.png` (alias, menu not captured) |
| Open With | yes | - | Qt has `Open With`, wx not yet | MISSING |
| Edit | yes | yes (via `open_local`) | | |
| Edit in New Window | yes | yes (`open_new_window`) | | |
| New Tab | yes (middle-click) | yes (`Ctrl+T`) | | |
| Rename (F2) | yes | yes (`LocalBrowserModel.rename_at`) | F2 | |
| Delete (Del) | yes | yes | Del | |
| Copy (Ctrl+C) | yes | yes | Ctrl+C | |
| Cut (Ctrl+X) | yes | yes | Ctrl+X | |
| Paste (Ctrl+V) | yes | yes | Ctrl+V | |
| New Folder | yes | yes | | `wx/38-files-local-context-background.png` (alias) |
| Copy Path | yes | yes | | |
| Undo Move | yes (remote) | yes (`_wx_remote_undo`) | Ctrl+Z | |
| Refresh (F5) | yes | yes | F5 | |

**Context Menus - Files Remote**

Same as local but with `Upload`/`Download` instead of `Open`. Wx captures `39-files-remote-context-single-file.png` (alias, menu popup not in window grab). Qt remote context not captured (MISSING).

**Context Menus - Jobs**

| Action | Qt | wx | Notes | Screenshot |
|--------|----|----|-------|------------|
| Refresh | yes | yes | | |
| Open Output | yes | yes (`show_job_output`) | | |
| Cancel Job | yes | yes | | |
| Show Details (`scontrol`) | yes | yes (`show_job_details` via Accounting group) | | |
| Refresh sacct | - | yes (`sacct_button`) | wx only | |

**Context Menus - Editor**

| Action | Qt | wx | Notes |
|--------|----|----|-------|
| Save | yes | yes | |
| Save As | yes | - (wx Save covers) | |
| Lint | yes | yes | |
| Run/Submit | yes | yes (Submit/Save+Submit) | |
| New from Template | yes | yes | |
| Close Tab | yes | yes | |

**Screenshot notes:** Real menu popup is a separate window; `win.grab()` / `ImageGrab.grab(window=handle)` captures main window only, not popup. Therefore `150-menu-file.png` etc are aliases of main window with menu bar visible but menu not open. Real context menu capture requires screen-region grab while menu is open (MISSING). Manifest marks those as `MISSING` where not achieved; closest real state is main window with menu bar.

