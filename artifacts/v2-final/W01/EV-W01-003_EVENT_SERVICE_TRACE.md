# EV-W01-003 — Event/Service Trace Sample

**Pinned SHA:** `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87`
**Generated:** 2026-09-15

---

## Trace 1: Settings Menu → Real Backend

```
Menu > Settings (menu.settings)
  → wx.EVT_MENU
  → _dispatch("APP-SETTINGS", frame, lifecycle, session_state)
  → wx_settings_view.show_settings(parent=parent)
  → _build_settings(parent, model, settings=None, apply=None, embedded=False)
  → WxSettingsModel reads from config/storage.py
  → User modifies → Apply → config/storage.py write_settings()
  → Close dialog
```

**Verdict:** Real implementation chain. Menu item → dispatch → dialog → model → storage.

## Trace 2: Check for Updates → Real Backend

```
Menu > Check for Updates (menu.check_updates)
  → wx.EVT_MENU
  → _dispatch("APP-UPDATE-CHECK", frame, lifecycle, session_state)
  → wx_updater_view.WxUpdateDialog(frame, None)
  → dlg._build_for_state(STATE_CHECKING)
  → dlg.dlg.Show()
```

**Verdict:** Real implementation chain. Opens updater dialog in CHECKING state.

## Trace 3: Help Center → Real Backend

```
Menu > Help Center (menu.help_center)
  → wx.EVT_MENU
  → _dispatch("APP-HELP", frame, lifecycle, session_state)
  → wx_help.show_help(parent)
  → WxHelpModel() → HelpSearchIndex, CommandPalette, ShortcutPreferences
  → wx.Frame with sidebar, content, search
```

**Verdict:** Real implementation chain. Full help center with search, navigation, shortcuts.

## Trace 4: About → Real Backend (FIX-W01-002)

```
Menu > About (menu.about)
  → wx.EVT_MENU
  → _dispatch("APP-ABOUT", frame, lifecycle, session_state)
  → wx_about.show_about(parent=parent)
  → wx.Dialog with version, description, repo URL, license, notices
  → Platform-aware file opening
```

**Verdict:** Real implementation chain. Proper dialog with all required fields.

## Trace 5: Browse & Install Plugins → Real Backend

```
Menu > Browse & Install (menu.browse_install)
  → wx.EVT_MENU
  → _dispatch("PLUGIN-BROWSE", frame, lifecycle, session_state)
  → wx_plugins_view.show_plugins(parent=parent, initial_tab="discover")
  → _build_plugins(parent, model, root=None, install=None, embedded=False)
  → WxPluginManagerModel with registry, search, install, enable/disable
```

**Verdict:** Real implementation chain. Plugin manager with discover/installed/updates tabs.

## Trace 6: Send Logs → Real Backend

```
Menu > Send Logs (menu.send_logs)
  → wx.EVT_MENU
  → _dispatch("APP-SEND-LOGS", frame, lifecycle, session_state)
  → wx_send_logs_view.show_send_logs(parent=parent)
  → Log collection, diagnostics export
```

**Verdict:** Real implementation chain.

## Trace 7: Request Plugin → External

```
Menu > Request Plugin (menu.request_plugin)
  → wx.EVT_MENU
  → _dispatch("PLUGIN-REQUEST", frame, lifecycle, session_state)
  → from hpc_gui.ui.dialogs.plugin_manager_dialog import PLUGIN_REQUEST_URL
  → webbrowser.open(PLUGIN_REQUEST_URL)
```

**Verdict:** Real implementation chain. Opens external URL in browser.

## Trace 8: Language Switch → Real Backend

```
Language > English/Turkish
  → wx.EVT_MENU (radio items)
  → set_language(language)
  → i18n.set_language() → update all labels via refresh_labels()
  → All menu items, tab labels, status bar relabeled
```

**Verdict:** Real implementation chain. Language switch affects all visible labels.

## Trace 9: Local File Context Menu → Real Backend

```
Right-click on local file
  → EVT_CONTEXT_MENU
  → context_menu() → wx.Menu()
  → Menu items filtered by visible_actions()
  → run_action(action_id)
  → Dispatches to: open, edit, upload, rename, delete, copy, cut, paste, etc.
```

**Verdict:** Real implementation chain. 15 context-menu actions all wired to handlers.

## Trace 10: Remote File Context Menu → Real Backend

```
Right-click on remote file
  → EVT_CONTEXT_MENU
  → wx.Menu() with 20 items
  → run_action(action_id, selected, target_dir)
  → Dispatches to: open, edit, download, upload, rename, delete, submit_sbatch, etc.
```

**Verdict:** Real implementation chain. 20 context-menu actions all wired to handlers.
