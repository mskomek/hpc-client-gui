"""Dynamic wx plugin menu construction and action routing."""
from __future__ import annotations

from hpc_gui.core.i18n import current_language, subscribe_language_change
from hpc_gui.core.wx_errors import report_wx_action_error


def bind_plugin_menu(wx, frame, session_state, notebook, page_controls, plugins_menu, sep_plugins_bottom, act_plugin_updates, editor_panel, refresh_labels):
    sep_plugins_top = None
    # --- Plugin menu dynamic handling (framework-neutral contribution model) ---
    _wx_plugin_dynamic_items: list = []
    _wx_plugin_action_bindings: list = []
    def _ensure_wx_plugins_top_separator():
        nonlocal sep_plugins_top
        if sep_plugins_top is None or sep_plugins_top not in plugins_menu.GetMenuItems():
            try:
                items = list(plugins_menu.GetMenuItems())
                # Find Check for Plugin Updates position
                try:
                    idx = items.index(act_plugin_updates) + 1
                except ValueError:
                    idx = 3
                new_sep = plugins_menu.InsertSeparator(idx)
                sep_plugins_top = new_sep
                frame._wx_shell_plugins_sep_top = new_sep
            except Exception:
                pass
    def _remove_wx_plugins_top_separator():
        nonlocal sep_plugins_top
        if sep_plugins_top is not None:
            try:
                plugins_menu.Remove(sep_plugins_top)
                sep_plugins_top.Destroy()
            except Exception:
                pass
            sep_plugins_top = None
            frame._wx_shell_plugins_sep_top = None
    def _wx_current_context():
        try:
            from hpc_gui.plugins.ui_contributions import MenuContext
            sess = session_state.get("session") or {}
            connected = bool(sess.get("connected")) if isinstance(sess, dict) else False
            editor_active = False
            try:
                # Heuristic: editor panel is current page
                if "editor_panel" in locals() or "editor_panel" in globals():
                    pass
                # Use notebook current page check
                cur = notebook.GetCurrentPage() if hasattr(notebook, "GetCurrentPage") else None
                editor_active = cur is editor_panel if "editor_panel" in dir() else False
                # Fallback: check page_controls
                if not editor_active:
                    try:
                        ed_page = page_controls.get("NAV-EDITOR", {}).get("page")
                        editor_active = notebook.GetCurrentPage() is ed_page if ed_page else False
                    except Exception:
                        pass
            except Exception:
                pass
            file_selected = False
            from hpc_gui.core.i18n import current_language
            return MenuContext(connected=connected, editor_active=editor_active, file_selected=file_selected, language=current_language())
        except Exception:
            from hpc_gui.plugins.ui_contributions import MenuContext
            return MenuContext()
    def _wx_rebuild_plugins_menu():
        nonlocal _wx_plugin_dynamic_items, _wx_plugin_action_bindings, sep_plugins_top
        try:
            from hpc_gui.plugins.loader import load_installed_plugins
            from hpc_gui.plugins.ui_contributions import collect_plugin_menu_contributions, evaluate_when, get_display_label
            from hpc_gui.services.plugin_menu_actions import can_execute_action
            # Clear previous dynamic
            for item_id, handler in _wx_plugin_action_bindings:
                frame.Unbind(wx.EVT_MENU, handler=handler, id=item_id)
            _wx_plugin_action_bindings = []
            for item in list(_wx_plugin_dynamic_items):
                plugins_menu.DestroyItem(item)
            _wx_plugin_dynamic_items = []
            # Insertion point is before the stored bottom separator
            sep_before_request = sep_plugins_bottom
            # Collect contributions
            result = load_installed_plugins()
            contribs = collect_plugin_menu_contributions(result.plugins)
            ctx = _wx_current_context()
            for contrib in sorted(contribs, key=lambda c: (get_display_label(c.label, c.labels, ctx.language).casefold(), c.label.casefold(), c.plugin_id.casefold())):
                lang = ctx.language
                root_label = get_display_label(contrib.label, contrib.labels, lang)
                root_menu = wx.Menu()
                has_visible = False
                for item in contrib.items:
                    from hpc_gui.plugins.ui_contributions import PluginMenuAction, PluginMenuSeparator, PluginMenuSubmenu
                    if isinstance(item, PluginMenuSeparator):
                        root_menu.AppendSeparator()
                        has_visible = True
                        continue
                    if isinstance(item, PluginMenuSubmenu):
                        caps = frozenset(_get_wx_plugin_caps(contrib.plugin_id))
                        show = evaluate_when(item.when, ctx, caps)
                        if not show and item.unavailable == "hide":
                            continue
                        sub_label = get_display_label(item.label, item.labels, lang)
                        sub_menu = wx.Menu()
                        sub_has = False
                        for child in item.items:
                            if isinstance(child, PluginMenuSeparator):
                                sub_menu.AppendSeparator()
                                sub_has = True
                                continue
                            if isinstance(child, PluginMenuAction):
                                cond_ok = evaluate_when(child.when, ctx, caps)
                                if not cond_ok and child.unavailable == "hide":
                                    continue
                                a_label = get_display_label(child.label, child.labels, lang)
                                act = sub_menu.Append(wx.ID_ANY, a_label)
                                if not cond_ok and child.unavailable == "disable":
                                    act.Enable(False)
                                # Capability guard & unsupported wx tool check
                                owning = _find_wx_plugin(contrib.plugin_id)
                                allowed = False
                                if owning is not None:
                                    allowed, _ = can_execute_action(child.action, owning)
                                if not allowed or child.action == "plugin.open_trusted_tool":
                                    act.Enable(False)
                                else:
                                    # Bind with host-owned identity
                                    def make_handler(action=child.action, pid=contrib.plugin_id):
                                        def handler(_evt):
                                            _wx_dispatch_plugin_action(action, pid)
                                        return handler
                                    handler = make_handler()
                                    frame.Bind(wx.EVT_MENU, handler, act)
                                    _wx_plugin_action_bindings.append((act.GetId(), handler))
                                sub_has = True
                                has_visible = True
                        if sub_has:
                            if not show and item.unavailable == "disable":
                                for mi in sub_menu.GetMenuItems():
                                    try:
                                        mi.Enable(False)
                                    except Exception:
                                        pass
                            root_menu.AppendSubMenu(sub_menu, sub_label)
                            has_visible = True
                        else:
                            try:
                                sub_menu.Destroy()
                            except Exception:
                                pass
                        continue
                    if isinstance(item, PluginMenuAction):
                        caps = frozenset(_get_wx_plugin_caps(contrib.plugin_id))
                        cond_ok = evaluate_when(item.when, ctx, caps)
                        if not cond_ok and item.unavailable == "hide":
                            continue
                        a_label = get_display_label(item.label, item.labels, lang)
                        act = root_menu.Append(wx.ID_ANY, a_label)
                        if not cond_ok and item.unavailable == "disable":
                            act.Enable(False)
                        owning = _find_wx_plugin(contrib.plugin_id)
                        allowed = False
                        if owning is not None:
                            allowed, _ = can_execute_action(item.action, owning)
                        # Disable unsupported wx tool actions
                        if not allowed or item.action == "plugin.open_trusted_tool":
                            act.Enable(False)
                        else:
                            def make_handler(action=item.action, pid=contrib.plugin_id):
                                def handler(_evt):
                                    _wx_dispatch_plugin_action(action, pid)
                                return handler
                            handler = make_handler()
                            frame.Bind(wx.EVT_MENU, handler, act)
                            _wx_plugin_action_bindings.append((act.GetId(), handler))
                        has_visible = True
                if has_visible:
                    # Insert before bottom separator
                    if sep_before_request:
                        items_now = list(plugins_menu.GetMenuItems())
                        idx = items_now.index(sep_before_request)
                        inserted = plugins_menu.Insert(idx, wx.ID_ANY, root_label, root_menu)
                    else:
                        inserted = plugins_menu.AppendSubMenu(root_menu, root_label)
                    _wx_plugin_dynamic_items.append(inserted)
                else:
                    try:
                        root_menu.Destroy()
                    except Exception:
                        pass
            # Exactly one separator when no visible dynamic roots - top physically present only when needed
            try:
                has_any = len(_wx_plugin_dynamic_items) > 0
                if has_any:
                    _ensure_wx_plugins_top_separator()
                else:
                    _remove_wx_plugins_top_separator()
                # Bottom separator always remains
                try:
                    sep_plugins_bottom.Enable(True)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception as e:
            try:
                import logging
                logging.getLogger("hpc_gui.wx_shell").warning("wx rebuild plugins menu failed: %s", e, exc_info=e)
            except Exception:
                pass
    def _get_wx_plugin_caps(plugin_id: str):
        try:
            from hpc_gui.plugins.loader import load_installed_plugins
            res = load_installed_plugins()
            for inst in res.plugins:
                if inst.manifest.id == plugin_id:
                    return tuple(inst.manifest.capabilities or ())
        except Exception:
            pass
        return ()
    def _find_wx_plugin(plugin_id: str):
        try:
            from hpc_gui.plugins.loader import load_installed_plugins
            res = load_installed_plugins()
            for inst in res.plugins:
                if inst.manifest.id == plugin_id:
                    return inst
        except Exception:
            pass
        return None
    def _wx_dispatch_plugin_action(action: str, plugin_id: str):
        try:
            from hpc_gui.services.plugin_menu_actions import dispatch_plugin_menu_action
            from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost
            plugin = _find_wx_plugin(plugin_id)
            if plugin is None:
                # W04 FIX-W04-A (DEF-W04-001): a stale plugin-menu click
                # (menu rebuild raced an uninstall/disable) must be visible
                # and diagnosable, never a silent no-op. No exception exists
                # here, so the helper mints a fresh diagnostic code.
                report_wx_action_error(
                    frame,
                    area="PLUGIN",
                    message_key="plugins.action_failed",
                    technical_detail=f"{plugin_id}:{action}",
                )
                return
            editor_page = None
            try:
                editor_page = page_controls.get("NAV-EDITOR", {}).get("page")
            except Exception:
                pass
            host = WxPluginMenuHost(editor_page=editor_page)
            dispatch_plugin_menu_action(action, plugin, host)
        except Exception as exc:
            # W04 FIX-W04-A (DEF-W04-001): a log-only failure left the UI in
            # a success-looking state; report a visible coded error instead.
            # The helper keeps the structured traceback log, so no log detail
            # is lost.
            report_wx_action_error(
                frame, area="PLUGIN", message_key="plugins.action_failed", exc=exc
            )
    # Bind menu open to rebuild (evaluate dynamic state when menu is about to open)
    try:
        frame.Bind(wx.EVT_MENU_OPEN, lambda evt: (_wx_rebuild_plugins_menu(), evt.Skip()) if evt.GetMenu() is plugins_menu else evt.Skip())
    except Exception:
        pass
    # Initial build
    try:
        _wx_rebuild_plugins_menu()
    except Exception:
        pass

    frame._wx_rebuild_plugins_menu = _wx_rebuild_plugins_menu
    # W04 FIX-W04-A: expose the dynamic plugin-action dispatcher for the
    # support-freeze regression suite (same pattern as the rebuild hook).
    frame._wx_dispatch_plugin_action = _wx_dispatch_plugin_action

    subscribe_language_change(refresh_labels)
