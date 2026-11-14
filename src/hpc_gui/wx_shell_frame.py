"""Compose the top-level wx shell frame and embedded feature views."""
from __future__ import annotations

from hpc_gui.wx_lifecycle import WxLifecycleController
from hpc_gui import __version__
from hpc_gui.wx_shell_connections import _connection_callbacks
from hpc_gui.wx_shell_connection_switch import install_connection_switch_guard
from hpc_gui.wx_shell_events import _directories_callbacks
from hpc_gui.wx_shell_dispatch import _dispatch
from hpc_gui.wx_shell_files import _editor_action_factory
from hpc_gui.wx_shell_jobs import _jobs_callbacks
from hpc_gui.wx_shell_events import _logs_callbacks
from hpc_gui.wx_shell_terminal import _run_shell_in_terminal
from hpc_gui.core.i18n import current_language, set_language, t


from hpc_gui.wx_shell_teardown import build_shell_close_handler
from hpc_gui.wx_shell_window_support import (
    _make_tray, _restore_main_window_state, _save_main_window_state,
    _update_shell_status_text,
)


def _repaint_translated_shell(wx, frame):
    """Repaint a shell whose labels changed under a live language switch.

    wxGTK redraws buttons and menus on SetLabel, but StaticText keeps the
    pixels it painted before the switch, so the body keeps the old language
    until every static label is invalidated explicitly.
    """
    def invalidate(window):
        for child in window.GetChildren():
            if isinstance(child, (wx.StaticText, wx.StaticBox)):
                child.InvalidateBestSize()
                child.Refresh()
            invalidate(child)

    try:
        if frame.IsBeingDeleted():
            return
        invalidate(frame)
        frame.Layout()
        frame.Refresh(True)
        frame.Update()
    except Exception:
        pass

def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_state=None, defer_terminal_webview=False):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed; use the default Qt runtime") from exc
    if app is None:
        app = wx.GetApp()
        if app is None:
            app = wx.App(False)
    # Keep App alive for the lifetime of the frame (prevents PyNoAppError on dynamic wx.Menu creation)
    lifecycle = lifecycle or WxLifecycleController()
    session_state = session_state or {"session": None, "generation": 0}
    from hpc_gui.wx_shell_sizing import shell_sizes

    default_size, min_size = shell_sizes(wx)
    frame = wx.Frame(None, title=f"{t('app.title')} {__version__}", size=default_size)
    frame._wx_app = app
    # Spec §3 asks for 1440×900 / 1280×760; on a smaller desktop those numbers
    # are clamped to the work area so the shell is not pushed off screen.
    frame.SetMinSize(wx.Size(*min_size))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    menubar = wx.MenuBar()
    # --- Menu ---
    menu_menu = wx.Menu()
    menu_items = {}
    # Settings
    act_settings = menu_menu.Append(wx.ID_ANY, t("menu.settings"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("APP-SETTINGS", frame, lifecycle, session_state), act_settings)
    menu_items["settings"] = act_settings
    # Check for Updates
    act_updates = menu_menu.Append(wx.ID_ANY, t("menu.check_updates"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("APP-UPDATE-CHECK", frame, lifecycle, session_state), act_updates)
    menu_items["check_updates"] = act_updates
    # Command Palette omitted (no real palette UI) – do not miswire to Help
    menu_menu.AppendSeparator()
    act_exit = menu_menu.Append(wx.ID_EXIT, t("menu.exit"))
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), act_exit)
    menu_items["exit"] = act_exit
    menubar.Append(menu_menu, t("menu.menu"))
    # --- Plugins ---
    plugins_menu = wx.Menu()
    act_browse = plugins_menu.Append(wx.ID_ANY, t("menu.browse_install"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-BROWSE", frame, lifecycle, session_state), act_browse)
    act_manage = plugins_menu.Append(wx.ID_ANY, t("menu.manage_installed"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-MANAGE", frame, lifecycle, session_state), act_manage)
    act_plugin_updates = plugins_menu.Append(wx.ID_ANY, t("menu.check_plugin_updates"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-UPDATES", frame, lifecycle, session_state), act_plugin_updates)
    # Dynamic plugin roots will be inserted here (between the two separators) - top separator created on demand
    sep_plugins_bottom = plugins_menu.AppendSeparator()
    act_request = plugins_menu.Append(wx.ID_ANY, t("menu.request_plugin"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-REQUEST", frame, lifecycle, session_state), act_request)
    menubar.Append(plugins_menu, t("menu.plugins"))
    frame._wx_shell_plugins_sep_bottom = sep_plugins_bottom
    # --- Help ---
    help_menu = wx.Menu()
    help_items = {}
    act_help = help_menu.Append(wx.ID_HELP, t("menu.help_center"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("APP-HELP", frame, lifecycle, session_state), act_help)
    help_items["help"] = act_help
    help_items["tour"] = None
    help_menu.AppendSeparator()
    act_logs = help_menu.Append(wx.ID_ANY, t("menu.send_logs"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("APP-SEND-LOGS", frame, lifecycle, session_state), act_logs)
    help_items["logs"] = act_logs
    help_menu.AppendSeparator()
    act_about = help_menu.Append(wx.ID_ABOUT, t("menu.about"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("APP-ABOUT", frame, lifecycle, session_state), act_about)
    help_items["about"] = act_about
    menubar.Append(help_menu, t("menu.help"))
    language_menu = wx.Menu()
    language_items = {}
    for language, key in (("en", "english"), ("tr", "turkish")):
        item = language_menu.AppendRadioItem(wx.ID_ANY, t(f"language.{key}"))
        item.Check(current_language() == language)
        language_items[language] = item
        frame.Bind(wx.EVT_MENU, lambda _event, language=language: set_language(language), item)
    menubar.Append(language_menu, t("help.language"))
    version_menu = wx.Menu()
    version_item = version_menu.Append(wx.ID_ANY, f"v{__version__}")
    version_item.Enable(False)
    menubar.Append(version_menu, f"v{__version__}")
    frame.SetMenuBar(menubar)
    # Keep references for refresh
    frame._wx_shell_menubar = menubar
    frame._wx_shell_menu_menu = menu_menu
    frame._wx_shell_plugins_menu = plugins_menu
    frame._wx_shell_help_menu = help_menu
    frame._wx_shell_menu_items = menu_items
    frame._wx_shell_help_items = help_items
    frame._wx_shell_plugins_before = sep_plugins_bottom
    # For compatibility with old tests that check COMMAND_REGISTRY usage, keep dummy but not dumping
    command_items = []  # no longer dumping all shell commands under Help
    notebook = wx.Notebook(panel)
    session_state["_embedded_main_notebook"] = notebook
    page_controls = {}

    # Build embedded panels using shared helpers (panels created once, not lazily)
    from hpc_gui.wx_connection import build_connection_panel
    from hpc_gui.wx_directories_view import build_directories_panel
    from hpc_gui.wx_editor_view import build_editor_panel
    from hpc_gui.wx_jobs import build_jobs_panel
    from hpc_gui.wx_logs_view import build_logs_panel

    # Connection
    _conn = _connection_callbacks(session_state, frame, lifecycle)
    connection_panel = build_connection_panel(notebook, **_conn)
    notebook.AddPage(connection_panel, t("tabs.login"), False)
    page_controls["APP-CONNECT"] = {"page": connection_panel}
    connection_model = getattr(connection_panel, "_wx_connection_model", None)
    controller = getattr(connection_model, "controller", None)
    previous_state_emitter = getattr(controller, "_emit", None)
    if controller is not None:
        def update_shell_connection_status(state):
            if callable(previous_state_emitter):
                previous_state_emitter(state)
            value = str(getattr(state, "value", state))

            def apply_status():
                session_state["connection_status"] = value
                _update_shell_status_text(frame, session_state)

            try:
                wx.CallAfter(apply_status)
            except Exception:
                pass

        controller._emit = update_shell_connection_status
    # Transport-loss reports (disconnect_cb) must invalidate the canonical
    # shell session too, not just the connection panel's controller, so no
    # domain keeps resolving a dead transport (CONN-005/TODO-007).
    try:
        _conn_model = getattr(connection_panel, "_wx_connection_model", None)
        if _conn_model is not None:
            _conn_model._session_invalidated_hook = _conn["on_disconnected"]
            install_connection_switch_guard(
                wx, connection_panel, session_state, _conn["on_disconnected"]
            )
    except Exception:
        pass

    # Terminal — right of Connection per user request (Connection | Terminal | Jobs | ...)
    from hpc_gui.wx_terminal import build_terminal_panel as _build_terminal_panel
    _term_session = session_state.get("session") or {}
    _term_ssh = _term_session.get("ssh")
    if defer_terminal_webview:
        terminal_page = wx.Panel(notebook)
        terminal_sizer = wx.BoxSizer(wx.VERTICAL)
        terminal_page.SetSizer(terminal_sizer)
        terminal_page.SetMinSize(wx.Size(400, 200))
        notebook.AddPage(terminal_page, t("help.section_terminal"), False)
        session_state["_embedded_terminal_panel"] = None
        page_controls["NAV-TERMINAL"] = {"page": terminal_page, "panel": terminal_page}

        def mount_terminal():
            if terminal_page.IsBeingDeleted():
                return
            live_session = session_state.get("session") or {}
            live_ssh = live_session.get("ssh") if isinstance(live_session, dict) else None
            real_panel = _build_terminal_panel(
                terminal_page, ssh=live_ssh or _term_ssh, lifecycle=lifecycle
            )
            terminal_sizer.Add(real_panel, 1, wx.EXPAND)
            terminal_page.Layout()
            session_state["_embedded_terminal_panel"] = real_panel
            controls = page_controls["NAV-TERMINAL"]
            term_controls = getattr(real_panel, "_wx_terminal_controls", {})
            controls.update(term_controls)
            controls.update({"output": term_controls.get("output"), "panel": real_panel})

            def close_terminal():
                callback = getattr(real_panel, "_wx_terminal_close", None) or getattr(real_panel, "close", None)
                if callable(callback):
                    callback()

            terminal_page._wx_host_close = close_terminal

        wx.CallLater(1000, mount_terminal)
    else:
        terminal_page = _build_terminal_panel(notebook, ssh=_term_ssh, lifecycle=lifecycle)
        session_state["_embedded_terminal_panel"] = terminal_page
        notebook.AddPage(terminal_page, t("help.section_terminal"), False)
        _term_controls = getattr(terminal_page, "_wx_terminal_controls", {})
        page_controls["NAV-TERMINAL"] = {"page": terminal_page, **_term_controls, "output": _term_controls.get("output"), "panel": terminal_page}

    # Jobs & Outputs
    _jobs = _jobs_callbacks(session_state, frame, lifecycle)
    jobs_panel = build_jobs_panel(notebook, **_jobs)
    session_state["_embedded_jobs_panel"] = jobs_panel
    notebook.AddPage(jobs_panel, t("tabs.jobs_outputs"), False)
    page_controls["NAV-JOBS"] = {"page": jobs_panel}

    # Directories (splitter with two remote panes)
    _dirs = _directories_callbacks(session_state, frame, lifecycle)
    directories_panel = build_directories_panel(notebook, **_dirs)
    notebook.AddPage(directories_panel, t("tabs.directories"), False)
    page_controls["NAV-DIRECTORIES"] = {"page": directories_panel}
    session_state["_embedded_directories_panel"] = directories_panel

    from hpc_gui.wx_shell_files_surface import build_files_surface
    build_files_surface(wx, frame, notebook, page_controls, session_state, lifecycle, t)
    from hpc_gui.wx_shell_layout import install_shell_splitter_ratios

    install_shell_splitter_ratios(wx, directories_panel, session_state)

    # Script Editor
    _editor_kwargs = {"action_factory": _editor_action_factory(session_state)}
    editor_panel = build_editor_panel(notebook, **_editor_kwargs)
    session_state["_embedded_editor_panel"] = editor_panel
    notebook.AddPage(editor_panel, t("tabs.editor"), False)
    page_controls["NAV-EDITOR"] = {"page": editor_panel}

    # Logs
    _logs = _logs_callbacks(session_state, frame, lifecycle)
    logs_panel = build_logs_panel(notebook, **_logs)
    notebook.AddPage(logs_panel, t("tabs.logs"), False)
    page_controls["NAV-LOGS"] = {"page": logs_panel}
    # Spec §4: panel padding 12px, §3 content expands with window
    root.Add(notebook, 1, wx.EXPAND | wx.ALL, 12)
    panel.SetSizer(root)
    frame.CreateStatusBar()
    frame.SetStatusText(t("common.ready"))

    def refresh_labels(_language=None):
        frame.SetTitle(f"{t('app.title')} {__version__}")
        # W55 A1 (HPC-W10-GJ2-030): retranslation must not clobber a live
        # connected indicator back to idle.
        _update_shell_status_text(frame, session_state)
        try:
            menubar = frame.GetMenuBar()
            menubar.SetMenuLabel(0, t("menu.menu"))
            menubar.SetMenuLabel(1, t("menu.plugins"))
            menubar.SetMenuLabel(2, t("menu.help"))
            menubar.SetMenuLabel(3, t("help.language"))
            menubar.SetMenuLabel(4, f"v{__version__}")
            # Update menu items
            if act_settings:
                menubar.SetLabel(act_settings.GetId(), t("menu.settings"))
            if act_updates:
                menubar.SetLabel(act_updates.GetId(), t("menu.check_updates"))
            if act_exit:
                menubar.SetLabel(act_exit.GetId(), t("menu.exit"))
            if act_browse:
                menubar.SetLabel(act_browse.GetId(), t("menu.browse_install"))
            if act_manage:
                menubar.SetLabel(act_manage.GetId(), t("menu.manage_installed"))
            if act_plugin_updates:
                menubar.SetLabel(act_plugin_updates.GetId(), t("menu.check_plugin_updates"))
            if act_request:
                menubar.SetLabel(act_request.GetId(), t("menu.request_plugin"))
            if act_help:
                menubar.SetLabel(act_help.GetId(), t("menu.help_center"))
            if act_logs:
                menubar.SetLabel(act_logs.GetId(), t("menu.send_logs"))
            if act_about:
                menubar.SetLabel(act_about.GetId(), t("menu.about"))
            try:
                tour_act = help_items.get("tour")
                if tour_act:
                    menubar.SetLabel(tour_act.GetId(), t("menu.quick_tour"))
            except Exception:
                pass
            # Refresh dynamic plugin menu labels without restart
            try:
                rebuild_plugins_menu = getattr(frame, "_wx_rebuild_plugins_menu", None)
                if callable(rebuild_plugins_menu):
                    rebuild_plugins_menu()
            except Exception:
                pass
        except Exception:
            pass
        for index, title_key in enumerate(("tabs.login", "help.section_terminal", "tabs.jobs_outputs", "tabs.directories", "tabs.ftp", "tabs.editor", "tabs.logs")):
            notebook.SetPageText(index, t(title_key))
        for command, item in command_items:
            try:
                menu.SetLabel(item.GetId(), command.label())
            except Exception:
                pass
        for language, item in language_items.items():
            try:
                language_menu.SetLabel(item.GetId(), t("help.english" if language == "en" else "help.turkish"))
                item.Check(current_language() == language)
            except Exception:
                pass
        # Files header row
        try:
            controls = page_controls["NAV-FILES"]
            controls["transfer_type_label"].SetLabel(t("ftp.transfer_type"))
            choice = controls["transfer_choice"]
            current_sel = choice.GetSelection() if choice.GetCount() else 0
            choice.Clear()
            for key in ("ftp.mode_auto", "ftp.mode_binary", "ftp.mode_ascii"):
                choice.Append(t(key))
            choice.SetSelection(current_sel if 0 <= current_sel < choice.GetCount() else 0)
            controls["effective_label"].SetLabel(
                t("ftp.effective_type").format(mode=controls["current_effective_mode"]())
            )
            controls["sync_cb"].SetLabel(t("ftp.sync_browsing"))
            controls["compare_btn"].SetLabel(t("ftp.compare_directories"))
            controls["compare_btn"].SetToolTip(t("ftp.compare_directories_tooltip"))
            controls["upload_selected"].SetLabel(t("ftp.upload_selected"))
            controls["download_selected"].SetLabel(t("ftp.download_selected"))
        except Exception:
            pass
        # wxGTK keeps painting the pre-switch pixels for static labels. The
        # repaint must run once every panel's relabel listener has finished,
        # so it is deferred instead of done inside this callback.
        if frame.IsShown():
            wx.CallAfter(_repaint_translated_shell, wx, frame)
    from hpc_gui.wx_shell_plugins import bind_plugin_menu
    bind_plugin_menu(
        wx, frame, session_state, notebook, page_controls, plugins_menu,
        sep_plugins_bottom, act_plugin_updates, editor_panel, refresh_labels,
    )

    from hpc_gui.wx_shell_window_events import create_window_event_state
    chrome_windows, shell_ref = create_window_event_state(
        wx, frame, lifecycle, session_state
    )

    tray = _make_tray(wx, frame, tray_factory)

    session_state["run_shell_in_terminal"] = lambda paths: _run_shell_in_terminal(
        session_state, frame, lifecycle, paths
    )

    def destroy_tray():
        if tray is not None:
            tray.destroy()

    if tray is not None:
        lifecycle.set_tray_notifier(tray.notify)
        lifecycle.register_cleanup(destroy_tray)

    # Backward compat aliases for old control dict
    menu = menu_menu
    command_items = []
    frame._wx_shell_controls = {"menu": menu, "language_menu": language_menu, "language_items": language_items, "version_menu": version_menu, "notebook": notebook, "pages": page_controls}
    frame._wx_shell_chrome_windows = chrome_windows
    frame._wx_shell_shell_ref = shell_ref
    frame._wx_shell_lifecycle = lifecycle
    frame._wx_shell_session_state = session_state
    frame._wx_shell_tray = tray

    close = build_shell_close_handler(
        wx, frame, notebook, lifecycle, page_controls, chrome_windows,
        shell_ref, refresh_labels, _save_main_window_state,
    )

    # W55 A1/A2 (HPC-W10-GJ2-029/038): keyboard accelerators for shell
    # navigation. Ctrl+1..7 selects notebook tabs; F1 opens Help. The table
    # is the keyboard-only traversal contract for the main shell.
    _wx_shell_accel_ids: dict = {}
    _wx_shell_accel_spec: list = []
    try:
        _accel_entries = []
        for _tab_index in range(min(7, int(notebook.GetPageCount()))):
            _tab_cmd = wx.NewIdRef()
            _wx_shell_accel_ids[int(_tab_cmd)] = _tab_index

            def _make_tab_handler(_idx=_tab_index):
                def _on_accel_tab(_evt):
                    try:
                        if frame.IsBeingDeleted():
                            return
                        if 0 <= _idx < int(notebook.GetPageCount()):
                            notebook.SetSelection(_idx)
                    except Exception:
                        pass
                return _on_accel_tab

            frame.Bind(wx.EVT_MENU, _make_tab_handler(), id=int(_tab_cmd))
            _accel_entries.append(
                wx.AcceleratorEntry(wx.ACCEL_CTRL, ord(str(_tab_index + 1)), int(_tab_cmd))
            )
            _wx_shell_accel_spec.append(
                (int(wx.ACCEL_CTRL), ord(str(_tab_index + 1)), int(_tab_cmd))
            )
        # Shell-level shortcuts honour settings.shortcut_preferences (Qt
        # parity); F1 stays the fallback when preferences are unreadable.
        try:
            from hpc_gui.core.platform import current_os
            from hpc_gui.wx_shortcuts import shell_accelerators, shell_bindings

            _shell_accels = shell_accelerators(wx, shell_bindings(current_os()))
        except Exception:
            _shell_accels = []
        if not any(cmd_id == "APP-HELP" for cmd_id, _f, _k in _shell_accels):
            _shell_accels.append(("APP-HELP", int(wx.ACCEL_NORMAL), int(wx.WXK_F1)))
        _accel_aliases = {"APP-HELP": "help", "APP-SETTINGS": "settings"}

        def _make_command_handler(command_id):
            def _on_accel_command(_evt):
                try:
                    if frame.IsBeingDeleted():
                        return
                    _dispatch(command_id, frame, lifecycle, session_state)
                except Exception:
                    pass
            return _on_accel_command

        for _cmd_id, _flags, _key in _shell_accels:
            _accel_cmd = wx.NewIdRef()
            _wx_shell_accel_ids[int(_accel_cmd)] = _accel_aliases.get(_cmd_id, _cmd_id)
            frame.Bind(wx.EVT_MENU, _make_command_handler(_cmd_id), id=int(_accel_cmd))
            _accel_entries.append(wx.AcceleratorEntry(_flags, _key, int(_accel_cmd)))
            _wx_shell_accel_spec.append((int(_flags), int(_key), int(_accel_cmd)))
        frame.SetAcceleratorTable(wx.AcceleratorTable(_accel_entries))
    except Exception:
        pass
    frame._wx_shell_accel_ids = _wx_shell_accel_ids
    frame._wx_shell_accel_spec = _wx_shell_accel_spec

    frame.Bind(wx.EVT_CLOSE, close)
    frame._wx_shell_close = close
    _restore_main_window_state(wx, frame, notebook)
    refresh_labels()
    return frame, lifecycle, session_state
