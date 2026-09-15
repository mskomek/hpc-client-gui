# EV-W01-004 — Context Menu Inventory

**Pinned SHA:** `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87`
**Generated:** 2026-09-15

---

## wx Context Menus (13 menus)

### 1. Local File Listing — `wx_local_files.py:549`
- Trigger: `EVT_CONTEXT_MENU` on list control
- Items: Open, Open with, Edit, Edit in new window, Run in terminal, Upload, Rename, Delete, Copy, Cut/Move, Paste, Copy Path, Refresh, New Tab, New Folder

### 2. Local Notebook Tabs — `wx_local_files.py:888`
- Trigger: `EVT_CONTEXT_MENU` on notebook
- Items: Close

### 3. Remote File Listing — `wx_remote_files_view.py:669`
- Trigger: `EVT_CONTEXT_MENU` on list control
- Items: Open, Edit, Edit in new window, Run in terminal, Follow/Track, Download, Upload, Copy, Move, Rename, Delete, Paste, Copy Path, Refresh, New Folder, New File, Permissions, Submit with sbatch, Favorite, New Tab

### 4. Remote Favorites Dropdown — `wx_remote_files_view.py:104`
- Trigger: Button click
- Items: [per-favorite], Add current directory

### 5. Remote History Dropdown — `wx_remote_files_view.py:121`
- Trigger: Button click
- Items: [per-history-entry], Clear history

### 6. Remote Follow/Track Submenu — `wx_remote_files_view.py:878`
- Trigger: From file listing context menu
- Items: Following (checkmark), Follow in new tab, Follow in new window, Follow in existing

### 7. Remote Notebook Tabs — `wx_remote_files_view.py:1249`
- Trigger: `EVT_CONTEXT_MENU` on notebook
- Items: Close

### 8. Connection Profile List — `wx_connection.py:939`
- Trigger: `EVT_CONTEXT_MENU` + `EVT_RIGHT_DOWN`
- Items: Connect, Edit, Duplicate, Delete

### 9. System Templates Popup — `wx_connection_dialog.py:803`
- Trigger: Button click
- Items: [builtin templates], [plugin templates], [user templates], Get more plugins

### 10. System Tray — `wx_shell.py:43`
- Trigger: Tray right-click
- Items: Close

### 11. Language Picker — `wx_shell.py:1179`
- Trigger: Button click
- Items: English, Turkish

### 12. Menu Bar — `wx_shell.py:92`
- Menu: Settings, Check for Updates, Exit
- Plugins: Browse & Install, Manage Installed, Check Plugin Updates, [dynamic roots], Request Plugin
- Help: Help Center, Send Logs, About
- Language: English, Turkish
- Version: v{version}

### 13. Dynamic Plugin Menus — `wx_shell.py:821`
- Trigger: `wx.EVT_MENU_OPEN` on plugins menu
- Items: Per-plugin contributions (actions, submenus, separators)

---

## Qt Context Menus (6 menus)

### 14. Local File Tree — `local_dir_panel.py:707`
- Items: Upload, Add files to queue, Open, Open with, Open in new tab, Edit, Edit in new window, Create directory, Create directory and enter, Refresh, Delete, Rename, Plugins submenu

### 15. Remote File Tree — `remote_dir_panel.py:2318`
- Items: Download, Save as, Add files to queue, View/Edit, Open in new tab, Favorite, Submit with sbatch, Run in terminal, Follow in Output 1/2, Create directory, Create new file, Refresh, Paste, Undo, Delete, Rename, Copy URL, Copy, Move, Permissions, ANSYS Lint, Plugins submenu

### 16. Connection Profiles — `login_widget.py:1172`
- Items: Connect, Edit, Duplicate

### 17. FTP Scratch/Home Panel — `ftp_widget.py:1251`
- Items: Set scratch as default, Set home as default

### 18. Transfer Activity Lists — `ftp_widget.py:729`
- Queue: Process queue, Stop and remove all, Remove selected, Set Priority submenu, Action after completion submenu
- Failed: Retry selected, Retry failed, Remove selected, Clear failed
- Completed: Remove selected, Clear completed

### 19. Transfer Errors List — `transfer_dialog.py:569`
- Items: Retry selected
