"""Main-window Plugins-menu ownership (Wave M01).

Mixin owning the static Plugins entries, the dynamic contribution roots,
action dispatch and the lazy Plugin Manager dialog launch. Cross-window
services are reached through ``self``; the ``show_exception`` helper is
resolved through the ``main_window`` facade at call time so existing
``hpc_gui.ui.main_window.show_exception`` patches keep working.
"""

from hpc_gui.core.i18n import t
from . import _main_window_contracts as _contracts


class _MainWindowPluginsMixin:
    def _open_plugin_requests(self):
        try:
            from hpc_gui.ui.dialogs.plugin_manager_dialog import PLUGIN_REQUEST_URL, PluginManagerDialog
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            url = PLUGIN_REQUEST_URL
            if PluginManagerDialog._is_allowed_plugin_request_url(url):
                opened = QDesktopServices.openUrl(QUrl(url))
                if not opened:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, t("plugins.dialog_title"), t("plugins.request_plugin_failed"))
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, t("plugins.dialog_title"), t("plugins.request_plugin_failed"))
        except Exception:
            pass

    def _open_plugins(self, initial_tab="discover"):
        try:
            from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
            dlg = PluginManagerDialog(self, initial_tab=initial_tab)
            # Live refresh without restart
            try:
                dlg.plugins_changed.connect(self._on_plugins_changed)
            except Exception:
                pass
            dlg.exec()
            # Post-exec safety refresh
            self._refresh_plugin_contributions_cache()
        except Exception as exc:
            self._logger.exception("Opening the Plugin Manager failed")
            _contracts.show_exception(
                self,
                title=t("plugins.dialog_title"),
                user_message=t("plugins.open_failed"),
                exc=exc,
                area="PLUGINS",
            )

    def _on_plugins_changed(self):
        try:
            self._refresh_plugin_contributions_cache()
        except Exception:
            pass

    def _refresh_plugin_contributions_cache(self):
        try:
            from hpc_gui.plugins.loader import load_installed_plugins
            from hpc_gui.plugins.ui_contributions import collect_plugin_menu_contributions
            # Collect only from enabled/compatible/corrupt-filtered plugins
            result = load_installed_plugins()
            # Filter disabled already done by loader; but we also need to keep only those with contribution
            self._plugin_contributions = collect_plugin_menu_contributions(result.plugins)
        except Exception as exc:
            self._logger.warning("Failed to refresh plugin contributions: %s", exc, exc_info=exc)
            self._plugin_contributions = []

    def _current_menu_context(self):
        try:
            from hpc_gui.plugins.ui_contributions import MenuContext
            from hpc_gui.core.i18n import current_language
            sess = getattr(self, "_session", None)
            connected = bool(sess and sess.get("connected")) if isinstance(sess, dict) else False
            editor_active = False
            try:
                editor_active = self.tabs.currentWidget() is self.editor
            except Exception:
                pass
            file_selected = False
            try:
                # Heuristic: if directories or ftp has selection
                if hasattr(self, "directories") and hasattr(self.directories, "panel_scratch"):
                    pnl = self.directories.panel_scratch
                    if hasattr(pnl, "tree") and hasattr(pnl.tree, "selectedItems"):
                        file_selected = bool(pnl.tree.selectedItems())
            except Exception:
                pass
            return MenuContext(connected=connected, editor_active=editor_active, file_selected=file_selected, language=current_language())
        except Exception:
            from hpc_gui.plugins.ui_contributions import MenuContext
            return MenuContext()

    def _rebuild_plugins_menu_dynamic(self):
        """Evaluate when-conditions on menu open, not on every tab change."""
        try:
            from hpc_gui.plugins.ui_contributions import evaluate_when, get_display_label
            from PySide6.QtGui import QAction
            from PySide6.QtWidgets import QMenu
            # Clear prior dynamic
            for act in list(getattr(self, "_plugins_dynamic_actions", [])):
                try:
                    self._plugins_menu.removeAction(act)
                    # If it's a menu's action, also delete menu
                    menu = act.menu() if hasattr(act, "menu") else None
                    if menu is not None:
                        menu.deleteLater()
                except Exception:
                    pass
            self._plugins_dynamic_actions = []
            ctx = self._current_menu_context()
            if not getattr(self, "_plugin_contributions", None):
                # No contributions at all -> still need to update separator visibility
                try:
                    has_any = False
                    if hasattr(self, "_plugins_dynamic_separator_top") and self._plugins_dynamic_separator_top is not None:
                        self._plugins_dynamic_separator_top.setVisible(has_any)
                    if hasattr(self, "_plugins_dynamic_before") and self._plugins_dynamic_before is not None:
                        self._plugins_dynamic_before.setVisible(True)
                except Exception:
                    pass
                return

            insert_before = getattr(self, "_plugins_dynamic_before", None)
            for contrib in sorted(self._plugin_contributions, key=lambda c: (get_display_label(c.label, c.labels, ctx.language).casefold(), c.label.casefold(), c.plugin_id.casefold())):
                lang = ctx.language
                root_label = get_display_label(contrib.label, contrib.labels, lang)
                # Create root menu for this plugin
                root_menu = QMenu(root_label, self)
                # For each item in contribution (preserve order)
                has_visible = False
                for item in contrib.items:
                    from hpc_gui.plugins.ui_contributions import PluginMenuAction, PluginMenuSeparator, PluginMenuSubmenu
                    if isinstance(item, PluginMenuSeparator):
                        # Separators inside root: only add if there is a previous non-separator and not at end – but normalization already handled
                        sep_act = QAction(self)
                        sep_act.setSeparator(True)
                        root_menu.addAction(sep_act)
                        has_visible = True
                        continue
                    if isinstance(item, PluginMenuSubmenu):
                        # Evaluate submenu when
                        caps = frozenset(self._get_plugin_capabilities(contrib.plugin_id))
                        show = evaluate_when(item.when, ctx, caps)
                        if not show:
                            if item.unavailable == "hide":
                                continue
                            # disable – show but disabled
                        sub_label = get_display_label(item.label, item.labels, lang)
                        sub_menu = QMenu(sub_label, self)
                        if not show and item.unavailable == "disable":
                            sub_menu.setEnabled(False)
                        # Add inner actions/separators
                        inner_visible = False
                        for child in item.items:
                            if isinstance(child, PluginMenuSeparator):
                                sep = QAction(self)
                                sep.setSeparator(True)
                                sub_menu.addAction(sep)
                                inner_visible = True
                                continue
                            if isinstance(child, PluginMenuAction):
                                caps2 = caps
                                cond_ok = evaluate_when(child.when, ctx, caps2)
                                if not cond_ok and child.unavailable == "hide":
                                    continue
                                a_label = get_display_label(child.label, child.labels, lang)
                                act = QAction(a_label, self)
                                if not cond_ok and child.unavailable == "disable":
                                    act.setEnabled(False)
                                # Check allowlist and capability guard before enabling
                                from hpc_gui.services.plugin_menu_actions import can_execute_action
                                # Resolve owning plugin object for dispatch
                                owning = self._find_installed_plugin(contrib.plugin_id)
                                if owning is not None:
                                    allowed, _reason = can_execute_action(child.action, owning)
                                    if not allowed:
                                        act.setEnabled(False)
                                else:
                                    act.setEnabled(False)
                                # Capture for dispatcher: host-owned action, pass owning plugin from host
                                act.triggered.connect(lambda _checked=False, a=child.action, p=contrib.plugin_id: self._dispatch_plugin_action(a, p))
                                sub_menu.addAction(act)
                                inner_visible = True
                                has_visible = True
                            else:
                                continue
                        if inner_visible:
                            # Normalize separators inside submenu already done
                            root_menu.addMenu(sub_menu)
                            has_visible = True
                        else:
                            sub_menu.deleteLater()
                            continue
                    elif isinstance(item, PluginMenuAction):
                        caps = frozenset(self._get_plugin_capabilities(contrib.plugin_id))
                        cond_ok = evaluate_when(item.when, ctx, caps)
                        if not cond_ok and item.unavailable == "hide":
                            continue
                        a_label = get_display_label(item.label, item.labels, lang)
                        act = QAction(a_label, self)
                        if not cond_ok and item.unavailable == "disable":
                            act.setEnabled(False)
                        from hpc_gui.services.plugin_menu_actions import can_execute_action
                        owning = self._find_installed_plugin(contrib.plugin_id)
                        if owning is not None:
                            allowed, _reason = can_execute_action(item.action, owning)
                            if not allowed:
                                act.setEnabled(False)
                        else:
                            act.setEnabled(False)
                        act.triggered.connect(lambda _checked=False, a=item.action, p=contrib.plugin_id: self._dispatch_plugin_action(a, p))
                        root_menu.addAction(act)
                        has_visible = True
                if has_visible:
                    # Insert before bottom separator
                    if insert_before is not None:
                        self._plugins_menu.insertMenu(insert_before, root_menu)
                        # Keep action reference for removal
                        self._plugins_dynamic_actions.append(root_menu.menuAction())
                    else:
                        action = self._plugins_menu.addMenu(root_menu)
                        self._plugins_dynamic_actions.append(action)
                else:
                    root_menu.deleteLater()
            # Separator visibility: exactly one when no visible dynamic roots
            try:
                has_any = len(self._plugins_dynamic_actions) > 0
                if hasattr(self, "_plugins_dynamic_separator_top") and self._plugins_dynamic_separator_top is not None:
                    self._plugins_dynamic_separator_top.setVisible(has_any)
                if hasattr(self, "_plugins_dynamic_before") and self._plugins_dynamic_before is not None:
                    self._plugins_dynamic_before.setVisible(True)
            except Exception:
                pass
        except Exception as exc:
            self._logger.warning("Failed to rebuild Plugins menu: %s", exc, exc_info=exc)

    def _get_plugin_capabilities(self, plugin_id: str) -> tuple[str, ...]:
        try:
            for contrib in getattr(self, "_plugin_contributions", []):
                if contrib.plugin_id == plugin_id:
                    # Need owning plugin's capabilities
                    p = self._find_installed_plugin(plugin_id)
                    if p:
                        return tuple(p.manifest.capabilities or ())
            # fallback
            from hpc_gui.plugins.loader import load_installed_plugins
            result = load_installed_plugins()
            for inst in result.plugins:
                if inst.manifest.id == plugin_id:
                    return tuple(inst.manifest.capabilities or ())
        except Exception:
            pass
        return ()

    def _find_installed_plugin(self, plugin_id: str):
        try:
            from hpc_gui.plugins.loader import load_installed_plugins
            res = load_installed_plugins()
            for inst in res.plugins:
                if inst.manifest.id == plugin_id:
                    return inst
        except Exception:
            pass
        return None

    def _dispatch_plugin_action(self, action: str, plugin_id: str):
        try:
            from hpc_gui.services.plugin_menu_actions import dispatch_plugin_menu_action
            from hpc_gui.ui.plugin_menu_qt_host import QtPluginMenuHost

            plugin = self._find_installed_plugin(plugin_id)
            if plugin is None:
                self._logger.warning("Plugin %s not found for action %s", plugin_id, action)
                return
            host = QtPluginMenuHost(editor_widget=getattr(self, "editor", None), host_window=self)
            dispatch_plugin_menu_action(action, plugin, host)
        except Exception as exc:
            self._logger.warning("Dispatch of %r for %s failed: %s", action, plugin_id, exc, exc_info=exc)
