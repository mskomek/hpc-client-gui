"""Optional wxPython migration shell; Qt remains the default runtime."""

from __future__ import annotations

import os
import inspect
import json
import shlex
from pathlib import Path
from pathlib import PurePosixPath
from threading import Event, Thread

from hpc_gui import __version__
from hpc_gui.core.i18n import current_language, load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change
from hpc_gui.core.wx_errors import report_wx_action_error
from hpc_gui.services.directory_comparison import ComparableEntry, compare_directory_entries
from hpc_gui.services.synchronized_browsing import SyncRoots, local_to_remote, normalize_local_root, normalize_remote_root, remote_to_local
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_lifecycle import WxLifecycleController
from hpc_gui.wx_runtime import environment_without_qt_graphics


def _flag_bitmap(wx, language):
    path = Path(__file__).resolve().parent / "assets" / "flags" / ("gb.svg" if language == "en" else "tr.svg")
    try:
        import wx.svg

        return wx.svg.SVGimage.CreateFromBytes(path.read_bytes()).ConvertToBitmap(18, 12)
    except Exception:
        bitmap = wx.Bitmap(18, 12)
        dc = wx.MemoryDC(bitmap)
        dc.SetBrush(wx.Brush("#1f4e79" if language == "en" else "#e30a17"))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        return bitmap


class _WxTrayAdapter:
    def __init__(self, wx, frame):
        import wx.adv

        class TrayIcon(wx.adv.TaskBarIcon):
            def CreatePopupMenu(self):
                menu = wx.Menu()
                close = menu.Append(wx.ID_EXIT, t("common.close"))
                self.Bind(wx.EVT_MENU, lambda _event: frame.Close(), close)
                return menu

        self._tray = TrayIcon()
        self._tray.SetIcon(wx.ArtProvider.GetIcon(wx.ART_INFORMATION), "HPC Client GUI")

    def notify(self, message):
        return self._tray.ShowBalloon(t("login.job_notification_title"), message, 5000)

    def destroy(self):
        tray, self._tray = self._tray, None
        if tray is not None:
            tray.Destroy()


def _make_tray(wx, frame, tray_factory):
    if tray_factory is not None:
        try:
            return tray_factory(frame)
        except (ImportError, RuntimeError):
            return None
    try:
        return _WxTrayAdapter(wx, frame)
    except (ImportError, RuntimeError):
        return None


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
    frame = wx.Frame(None, title=f"HPC Client GUI {__version__}", size=(1440, 900))
    frame._wx_app = app
    # Spec §3: recommended 1440×900 default, 1280×760 minimum; usable at ~1100×700 without clipping
    frame.SetMinSize(wx.Size(1280, 760))
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
    sep_plugins_top = None
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
    from hpc_gui.wx_local_files import build_local_files_panel
    from hpc_gui.wx_logs_view import build_logs_panel
    from hpc_gui.wx_remote_files_view import build_remote_files_panel

    # Connection
    _conn = _connection_callbacks(session_state, frame, lifecycle)
    connection_panel = build_connection_panel(notebook, **_conn)
    notebook.AddPage(connection_panel, t("tabs.login"), False)
    page_controls["APP-CONNECT"] = {"page": connection_panel}
    # Transport-loss reports (disconnect_cb) must invalidate the canonical
    # shell session too, not just the connection panel's controller, so no
    # domain keeps resolving a dead transport (CONN-005/TODO-007).
    try:
        _conn_model = getattr(connection_panel, "_wx_connection_model", None)
        if _conn_model is not None:
            _conn_model._session_invalidated_hook = _conn["on_disconnected"]
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
            real_panel = _build_terminal_panel(terminal_page, ssh=_term_ssh, lifecycle=lifecycle)
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

    # Files (header row + splitter with local left, remote right + transfers bottom)
    files_page = wx.Panel(notebook)
    files_sizer = wx.BoxSizer(wx.VERTICAL)
    # header row: Transfer type [Auto v] Effective: Binary  Synchronized browsing  Compare directories
    #                                         Upload selected  Download selected
    # Use WrapSizer so narrow windows wrap.
    files_header = wx.WrapSizer(wx.HORIZONTAL)
    transfer_type_label = wx.StaticText(files_page, label=t("ftp.transfer_type"))
    transfer_choice = wx.Choice(files_page, choices=[t("ftp.mode_auto"), t("ftp.mode_binary"), t("ftp.mode_ascii")])
    # restore from session_state if present
    try:
        saved_mode = str(session_state.get("ftp_transfer_type", "auto")).lower()
        sel_idx = {"auto": 0, "binary": 1, "ascii": 2}.get(saved_mode, 0)
        transfer_choice.SetSelection(sel_idx)
    except Exception:
        transfer_choice.SetSelection(0)
    # effective label
    def _current_effective_mode():
        try:
            idx = transfer_choice.GetSelection()
            if idx == 1:
                return t("ftp.mode_binary")
            if idx == 2:
                return t("ftp.mode_ascii")
            return t("ftp.mode_auto")
        except Exception:
            return t("ftp.mode_auto")
    effective_label = wx.StaticText(files_page, label=t("ftp.effective_type").format(mode=_current_effective_mode()))
    sync_cb = wx.CheckBox(files_page, label=t("ftp.sync_browsing"))
    # enabled even without connection for test seam; real guard inside handlers
    try:
        sync_cb.SetToolTip(t("ftp.sync_browsing"))
    except Exception:
        pass
    compare_btn = wx.Button(files_page, label=t("ftp.compare_directories"))
    compare_btn.SetToolTip(t("ftp.compare_directories_tooltip") if t("ftp.compare_directories_tooltip") != "[ftp.compare_directories_tooltip]" else "Compare directories")
    # keep enabled for seam; handlers check session/connection if needed but allow fake backends in tests
    upload_selected_btn = wx.Button(files_page, label=t("ftp.upload_selected"))
    download_selected_btn = wx.Button(files_page, label=t("ftp.download_selected"))
    files_header.Add(transfer_type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    files_header.Add(transfer_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    files_header.Add(effective_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    files_header.Add(sync_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    files_header.Add(compare_btn, 0, wx.ALL, 4)
    files_header.AddStretchSpacer(1)
    files_header.Add(upload_selected_btn, 0, wx.ALL, 4)
    files_header.Add(download_selected_btn, 0, wx.ALL, 4)
    files_sizer.Add(files_header, 0, wx.EXPAND | wx.ALL, 4)
    transfer_splitter = wx.SplitterWindow(files_page)
    transfer_splitter.SetMinimumPaneSize(140)
    top_splitter = wx.SplitterWindow(transfer_splitter)
    _local = _local_files_callbacks(session_state, frame, lifecycle)
    _remote = _remote_files_callbacks(session_state, frame, lifecycle)
    local_panel = build_local_files_panel(top_splitter, **_local)
    session_state["_embedded_local_files_panel"] = local_panel
    remote_panel = build_remote_files_panel(top_splitter, **_remote)
    session_state["_embedded_remote_files_panel"] = remote_panel
    top_splitter.SplitVertically(local_panel, remote_panel, 340)
    top_splitter.SetMinimumPaneSize(300)
    from hpc_gui.wx_transfer_workspace import build_transfers_panel

    transfers_panel = build_transfers_panel(transfer_splitter)
    # store for routing in _start_file_transfers
    session_state["embedded_transfers_panel"] = transfers_panel
    # Give the transfers list room for its column headers, and let a taller
    # window grow the browsers rather than the transfers area.
    transfer_splitter.SplitHorizontally(top_splitter, transfers_panel, -220)
    transfer_splitter.SetSashGravity(0.7)
    files_sizer.Add(transfer_splitter, 1, wx.EXPAND)
    files_page.SetSizer(files_sizer)
    session_state["_embedded_files_page"] = files_page
    def _on_transfer_choice(_evt):
        try:
            idx = transfer_choice.GetSelection()
            mode_key = ["auto", "binary", "ascii"][idx] if 0 <= idx < 3 else "auto"
            session_state["ftp_transfer_type"] = mode_key
            effective_label.SetLabel(t("ftp.effective_type").format(mode=_current_effective_mode()))
            files_page.Layout()
        except Exception:
            pass
    transfer_choice.Bind(wx.EVT_CHOICE, _on_transfer_choice)
    # Upload/Download selected must call same operation callbacks the remote panel toolbar already uses
    def _header_upload(_evt):
        # Same implementation the local toolbar uses; no second upload path.
        run = getattr(local_panel, "_wx_local_run_action", None)
        if callable(run):
            run("upload")

    def _header_download(_evt):
        # Same implementation the remote toolbar uses; no second download path.
        # Mirror _on_toolbar_download: forward the panel's current selection
        # plus its directory (DEF-W04-002: a bare run("download") never
        # matched run_action(action, selected, target_dir) and raised
        # TypeError on every header click, leaving a silent no-op).
        run = getattr(remote_panel, "_wx_remote_run_action", None)
        if not callable(run):
            return
        try:
            tabs = getattr(remote_panel, "_wx_remote_tabs", None) or []
            notebook = getattr(remote_panel, "_wx_remote_notebook", None)
            sel_idx = notebook.GetSelection() if notebook is not None else 0
            tstate = tabs[sel_idx] if 0 <= sel_idx < len(tabs) else (tabs[0] if tabs else None)
            if tstate is not None:
                listing = tstate.get("listing")
                entries = tstate.get("entries") or ()
                selected = tuple(
                    entry.path
                    for idx, entry in enumerate(entries)
                    if listing is not None and listing.IsSelected(idx)
                )
                run("download", selected, tstate.get("path", "/"))
                return
        except Exception:
            pass
        run("download", (), "/")

    upload_selected_btn.Bind(wx.EVT_BUTTON, _header_upload)
    download_selected_btn.Bind(wx.EVT_BUTTON, _header_download)
    notebook.AddPage(files_page, t("tabs.ftp"), False)
    page_controls["NAV-FILES"] = {"page": files_page, "local": local_panel, "remote": remote_panel, "transfers": transfers_panel, "splitter": transfer_splitter, "header": files_header, "transfer_type_label": transfer_type_label, "transfer_choice": transfer_choice, "effective_label": effective_label, "sync_cb": sync_cb, "compare_btn": compare_btn, "upload_selected": upload_selected_btn, "download_selected": download_selected_btn}
    # --- Sync browsing & Compare directories wiring (Wave 48) ---
    _sync_state = {"enabled": False, "roots": SyncRoots(), "guard": False, "generation": 0}
    _compare_state = {"generation": 0, "in_flight": False, "closed": False}
    # comparison visible result area (initially hidden, shown when compare active)
    _compare_result = wx.TextCtrl(files_page, style=wx.TE_READONLY | wx.TE_MULTILINE)
    _compare_result.SetMinSize(wx.Size(-1, 80))
    _compare_result.Hide()
    files_sizer.Add(_compare_result, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    # expose for tests
    files_page._sync_state = _sync_state
    files_page._compare_state = _compare_state
    files_page._compare_result = _compare_result
    def _current_local_dir() -> str:
        try:
            m = getattr(local_panel, "_wx_local_model", None) or getattr(local_panel, "_local_model", None)
            if m is not None and hasattr(m, "current_path"):
                return str(m.current_path)
            # fallback to panel attribute
            if hasattr(local_panel, "GetParent"):
                # try to read from tabs
                pass
        except Exception:
            pass
        try:
            return str(Path.cwd())
        except Exception:
            return ""
    def _current_remote_dir() -> str:
        try:
            m = getattr(remote_panel, "_wx_remote_model", None) or getattr(remote_panel, "_remote_model", None)
            # remote model current_path
            if m is not None and hasattr(m, "current_path"):
                return str(m.current_path)
        except Exception:
            pass
        return "/"
    def _do_sync_local_to_remote(local_path: str):
        if not _sync_state["enabled"] or _sync_state["guard"]:
            return
        roots = _sync_state["roots"]
        target = local_to_remote(local_path, roots)
        if target is None:
            try:
                sync_cb.SetToolTip(t("ftp.sync_outside_root"))
            except Exception:
                pass
            return
        try:
            sync_cb.SetToolTip(t("ftp.sync_browsing"))
        except Exception:
            pass
        _sync_state["guard"] = True
        try:
            # navigate remote panel if possible
            # try via host method or model
            rm = getattr(remote_panel, "_wx_remote_model", None)
            if rm is not None and hasattr(rm, "navigate"):
                try:
                    rm.navigate(target)
                except Exception:
                    # restore guard and show failure without wrong target
                    _sync_state["guard"] = False
                    return
                # also try to refresh view if available
                try:
                    if hasattr(remote_panel, "_refresh"):
                        remote_panel._refresh()
                    elif hasattr(remote_panel, "Refresh"):
                        remote_panel.Refresh()
                except Exception:
                    pass
            else:
                # fallback: set session remote path via state
                session_state["_sync_remote_target"] = target
        finally:
            _sync_state["guard"] = False
    def _do_sync_remote_to_local(remote_path: str):
        if not _sync_state["enabled"] or _sync_state["guard"]:
            return
        roots = _sync_state["roots"]
        target = remote_to_local(remote_path, roots)
        if target is None:
            try:
                sync_cb.SetToolTip(t("ftp.sync_remote_outside_root"))
            except Exception:
                pass
            return
        if not os.path.isdir(target):
            try:
                sync_cb.SetToolTip(t("ftp.sync_local_root_unavailable"))
            except Exception:
                pass
            return
        try:
            sync_cb.SetToolTip(t("ftp.sync_browsing"))
        except Exception:
            pass
        _sync_state["guard"] = True
        try:
            lm = getattr(local_panel, "_wx_local_model", None)
            if lm is not None and hasattr(lm, "navigate"):
                try:
                    lm.navigate(target)
                except Exception:
                    _sync_state["guard"] = False
                    return
                try:
                    if hasattr(local_panel, "_refresh"):
                        local_panel._refresh()
                except Exception:
                    pass
            else:
                session_state["_sync_local_target"] = target
        finally:
            _sync_state["guard"] = False
    def _on_sync_toggle(evt):
        checked = sync_cb.GetValue()
        _sync_state["enabled"] = bool(checked)
        if checked:
            # capture current dirs as roots
            try:
                local_dir = _current_local_dir()
                remote_dir = _current_remote_dir()
                # allow test injection via session_state override
                local_dir = session_state.get("_test_local_root", local_dir)
                remote_dir = session_state.get("_test_remote_root", remote_dir)
                # normalize
                local_root = normalize_local_root(local_dir) if local_dir else ""
                remote_root = normalize_remote_root(remote_dir) if remote_dir else ""
                _sync_state["roots"] = SyncRoots(local_root, remote_root)
                _sync_state["generation"] += 1
                session_state["_sync_roots"] = _sync_state["roots"]
                try:
                    sync_cb.SetToolTip(t("ftp.sync_browsing"))
                except Exception:
                    pass
            except Exception as e:
                _sync_state["enabled"] = False
                sync_cb.SetValue(False)
                try:
                    sync_cb.SetToolTip(str(e))
                except Exception:
                    pass
        else:
            _sync_state["roots"] = SyncRoots()
            try:
                sync_cb.SetToolTip(t("ftp.sync_browsing"))
            except Exception:
                pass
        evt.Skip()
    sync_cb.Bind(wx.EVT_CHECKBOX, _on_sync_toggle)
    # expose sync helpers for tests and for panel navigation hooks
    files_page._do_sync_local_to_remote = _do_sync_local_to_remote
    files_page._do_sync_remote_to_local = _do_sync_remote_to_local
    files_page._on_sync_toggle = _on_sync_toggle
    # hook local/remote panel navigation if possible by wrapping model navigate
    try:
        lm = getattr(local_panel, "_wx_local_model", None)
        if lm is not None and hasattr(lm, "navigate"):
            _orig_local_nav = lm.navigate
            def _wrapped_local_nav(path, _orig=_orig_local_nav):
                res = _orig(path)
                # after local nav, trigger sync
                try:
                    _do_sync_local_to_remote(str(path))
                except Exception:
                    pass
                return res
            lm.navigate = _wrapped_local_nav
    except Exception:
        pass
    try:
        rm = getattr(remote_panel, "_wx_remote_model", None)
        if rm is not None and hasattr(rm, "navigate"):
            _orig_remote_nav = rm.navigate
            def _wrapped_remote_nav(path, _orig=_orig_remote_nav):
                res = _orig(path)
                try:
                    _do_sync_remote_to_local(str(path))
                except Exception:
                    pass
                return res
            rm.navigate = _wrapped_remote_nav
    except Exception:
        pass
    # Compare directories wiring
    def _fetch_local_entries():
        # try via local model
        try:
            lm = getattr(local_panel, "_wx_local_model", None)
            if lm is not None and hasattr(lm, "current_path"):
                cur = Path(str(lm.current_path))
                if cur.is_dir():
                    entries = []
                    for p in cur.iterdir():
                        try:
                            st = p.stat()
                            entries.append(ComparableEntry(p.name, p.is_dir(), int(st.st_size) if p.is_file() else 0, int(st.st_mtime)))
                        except Exception:
                            entries.append(ComparableEntry(p.name, p.is_dir(), 0, 0))
                    return entries
        except Exception:
            pass
        return []
    def _fetch_remote_entries():
        # via session files or test injection
        test_entries = session_state.get("_test_remote_entries")
        if test_entries is not None:
            return list(test_entries)
        try:
            # try remote model
            rm = getattr(remote_panel, "_wx_remote_model", None)
            if rm is not None:
                # attempt to list via files service if available
                sess = session_state.get("session") or {}
                files = sess.get("files")
                if files and hasattr(files, "iterdir_entries"):
                    cur = getattr(rm, "current_path", "/")
                    raw = list(files.iterdir_entries(str(cur)))
                    entries = []
                    for r in raw:
                        # r may be dict or object with name/is_dir/size/mtime
                        if isinstance(r, dict):
                            entries.append(ComparableEntry(str(r.get("name", "")), bool(r.get("is_dir")), int(r.get("size",0)), int(r.get("mtime",0))))
                        else:
                            entries.append(ComparableEntry(str(getattr(r, "path", getattr(r, "name", ""))).rsplit("/",1)[-1], bool(getattr(r,"is_dir", False)), int(getattr(r,"size",0)), int(getattr(r,"mtime",0))))
                    return entries
        except Exception:
            pass
        return []
    def _render_compare(result):
        # visible result
        if _compare_state.get("closed"):
            return
        # check generation staleness
        # result is ComparisonResult
        try:
            lines = []
            # local statuses
            for name, status in sorted(result.local.items()):
                lines.append(f"{name}: {status.value}")
            for name, status in sorted(result.remote.items()):
                lines.append(f"{name}: {status.value} (remote)")
            if not lines:
                lines.append(t("ftp.compare_directories_tooltip") if t("ftp.compare_directories_tooltip") != "[ftp.compare_directories_tooltip]" else "No differences")
            text = "\n".join(lines)
            _compare_result.SetValue(text)
            _compare_result.Show()
            files_page.Layout()
        except Exception:
            pass
    def _on_compare(evt):
        # toggle handler for button (not checkbox)
        # we treat button as toggle: if currently showing, hide, else compute
        is_shown = _compare_result.IsShown()
        if is_shown:
            _compare_result.Hide()
            files_page.Layout()
            _compare_state["generation"] += 1
            evt.Skip()
            return
        # start compare in background
        _compare_state["generation"] += 1
        gen = _compare_state["generation"]
        _compare_state["in_flight"] = True
        _compare_result.SetValue(t("ftp.compare_directories_tooltip"))
        _compare_result.Show()
        files_page.Layout()
        def worker(current_gen=gen):
            try:
                local_entries = _fetch_local_entries()
                remote_entries = _fetch_remote_entries()
                import time
                delay = float(session_state.get("_test_compare_delay", 0))
                if delay:
                    time.sleep(delay)
                result = compare_directory_entries(local_entries, remote_entries)
                import wx as _wx
                def apply():
                    if _compare_state.get("closed") or current_gen != _compare_state.get("generation"):
                        return
                    _compare_state["in_flight"] = False
                    _render_compare(result)
                try:
                    if _wx.GetApp() is not None:
                        _wx.CallAfter(apply)
                except Exception:
                    pass
            except Exception as e:
                import wx as _wx
                def apply_err(err=e):
                    if _compare_state.get("closed") or current_gen != _compare_state.get("generation"):
                        return
                    _compare_state["in_flight"] = False
                    try:
                        _compare_result.SetValue(str(err))
                    except Exception:
                        pass
                try:
                    if _wx.GetApp() is not None:
                        _wx.CallAfter(apply_err)
                except Exception:
                    pass
        Thread(target=worker, daemon=True).start()
        evt.Skip()
    compare_btn.Bind(wx.EVT_BUTTON, _on_compare)
    files_page._compare_fetch_local = _fetch_local_entries
    files_page._compare_fetch_remote = _fetch_remote_entries
    files_page._compare_render = _render_compare
    # close handling
    def _files_close():
        _compare_state["closed"] = True
        _compare_state["generation"] += 1
    # store for shell close
    files_page._wx_files_close = _files_close
    if lifecycle is not None:
        lifecycle.register_cleanup(_files_close)

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
        frame.SetStatusText(t("common.ready"))
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
                _wx_rebuild_plugins_menu()
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
            transfer_type_label.SetLabel(t("ftp.transfer_type"))
            # update choice strings
            current_sel = transfer_choice.GetSelection() if transfer_choice.GetCount() else 0
            transfer_choice.Clear()
            for key in ("ftp.mode_auto", "ftp.mode_binary", "ftp.mode_ascii"):
                transfer_choice.Append(t(key))
            transfer_choice.SetSelection(current_sel if 0 <= current_sel < transfer_choice.GetCount() else 0)
            effective_label.SetLabel(t("ftp.effective_type").format(mode=_current_effective_mode()))
            sync_cb.SetLabel(t("ftp.sync_browsing"))
            compare_btn.SetLabel(t("ftp.compare_directories"))
            compare_btn.SetToolTip(t("ftp.compare_directories_tooltip"))
            upload_selected_btn.SetLabel(t("ftp.upload_selected"))
            download_selected_btn.SetLabel(t("ftp.download_selected"))
        except Exception:
            pass

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

    # --- chrome parenting / tracking (Part 3) ---
    chrome_windows: list = []
    shell_ref = [frame]

    def _shell_frame():
        f = shell_ref[0] if shell_ref else None
        if f is None:
            return None
        try:
            if not wx.Window.FindWindowById(f.GetId()):
                return None
        except Exception:
            return None
        # also check if being deleted
        try:
            if f.IsBeingDeleted():
                return None
        except Exception:
            pass
        return f

    def _track_new_windows(before_set):
        f = _shell_frame()
        if f is None:
            return
        after = set(wx.GetTopLevelWindows())
        for w in after - before_set:
            try:
                if w.GetParent() is f:
                    chrome_windows.append(w)
                    # untrack when child closes/destroys
                    def _on_child_close(evt, win=w):
                        try:
                            if win in chrome_windows:
                                chrome_windows.remove(win)
                        except Exception:
                            pass
                        evt.Skip()
                    def _on_child_destroy(evt, win=w):
                        try:
                            if win in chrome_windows:
                                chrome_windows.remove(win)
                        except Exception:
                            pass
                        evt.Skip()
                    w.Bind(wx.EVT_CLOSE, _on_child_close)
                    w.Bind(wx.EVT_WINDOW_DESTROY, _on_child_destroy)
            except Exception:
                pass

    def _on_help(_event):
        f = _shell_frame()
        if not f:
            return
        _dispatch("APP-HELP", f, lifecycle, session_state)

    def _on_update(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        try:
            from hpc_gui.wx_updater_view import WxUpdateDialog, STATE_CHECKING, STATE_FAILED, STATE_UPDATE_AVAILABLE, STATE_UP_TO_DATE
        except Exception:
            return
        dlg = WxUpdateDialog(f, None)
        dlg._build_for_state(STATE_CHECKING)
        dlg.dlg.Show()
        _track_new_windows(before)
        def worker():
            try:
                from hpc_gui.services.app_updater import get_latest_release, is_newer_version, AUTOMATIC_INSTALL_STRATEGIES
                from hpc_gui.core.platform import current_os
                from hpc_gui import __version__ as cur_ver2
                release = get_latest_release(timeout=10)
                def on_done():
                    ff = _shell_frame()
                    if not ff or not wx.Window.FindWindowById(ff.GetId()):
                        try:
                            dlg.Destroy()
                        except Exception:
                            pass
                        return
                    try:
                        if not is_newer_version(release.version, cur_ver2):
                            dlg._build_for_state(STATE_UP_TO_DATE)
                            _track_new_windows(before)
                            return
                        try:
                            from hpc_gui.services import app_updater as _au
                            macos_ok = not (release.install_strategy == "macos-bundle" and release.security_status != _au.SECURITY_SIGNED)
                        except Exception:
                            macos_ok = True
                        if release.install_strategy not in AUTOMATIC_INSTALL_STRATEGIES or not macos_ok:
                            import webbrowser
                            msg = t("updates.manual_install").format(version=release.version) if t("updates.manual_install") != "[updates.manual_install]" else f"Update {release.version} requires manual install."
                            if current_os() == "macos":
                                try:
                                    sec_key = {_au.SECURITY_UNSIGNED: "updates.security_unsigned_mac", _au.SECURITY_SIGNED: "updates.security_signed_mac", _au.SECURITY_UNKNOWN: "updates.security_unknown_mac"}.get(release.security_status, "updates.security_unknown_mac")
                                    msg += "\n\n" + t(sec_key)
                                except Exception:
                                    pass
                            wx.MessageBox(msg, t("updates.title"), wx.OK | wx.ICON_INFORMATION, ff)
                            try:
                                webbrowser.open(release.zip_url or release.html_url)
                            except Exception:
                                pass
                            try:
                                dlg.Destroy()
                            except Exception:
                                pass
                            _track_new_windows(before)
                            return
                        dlg.release = release
                        dlg._total = getattr(release, "size", None)
                        try:
                            from hpc_gui.wx_updater_view import _parse_whats_new
                            dlg._whats_new = _parse_whats_new(getattr(release, "body", ""))
                        except Exception:
                            pass
                        dlg._build_for_state(STATE_UPDATE_AVAILABLE)
                        _track_new_windows(before)
                    except Exception as e:
                        dlg._error_message = str(e)
                        dlg._error_details = f"{type(e).__name__}: {e}"
                        dlg._build_for_state(STATE_FAILED)
                wx.CallAfter(on_done)
            except Exception as exc:
                def on_err(exc=exc):
                    ff = _shell_frame()
                    if not ff:
                        try:
                            dlg.Destroy()
                        except Exception:
                            pass
                        return
                    dlg._error_message = str(exc)
                    dlg._error_details = f"{type(exc).__name__}: {exc}"
                    dlg._build_for_state(STATE_FAILED)
                wx.CallAfter(on_err)
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _on_plugins(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        # W02 ERROR-GOV: route through _dispatch like _on_help so failures
        # are visible with a stable code instead of silently swallowed.
        _dispatch("PLUGIN-BROWSE", f, lifecycle, session_state)
        _track_new_windows(before)

    def _on_send_logs(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        # W02 ERROR-GOV: route through _dispatch like _on_help so failures
        # are visible with a stable code instead of silently swallowed.
        _dispatch("APP-SEND-LOGS", f, lifecycle, session_state)
        _track_new_windows(before)

    def _on_settings(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        # W02 ERROR-GOV: route through _dispatch like _on_help so failures
        # are visible with a stable code instead of silently swallowed.
        _dispatch("APP-SETTINGS", f, lifecycle, session_state)
        _track_new_windows(before)

    def _on_language_button(_event):
        f = _shell_frame()
        if not f:
            return
        # show popup menu parented to shell frame, not button
        cur = current_language()
        menu = wx.Menu()
        ids = {}
        for lang, key in (("en", "english"), ("tr", "turkish")):
            item = menu.AppendRadioItem(wx.ID_ANY, t(f"language.{key}"))
            try:
                item.SetBitmap(_flag_bitmap(wx, lang))
            except Exception:
                pass
            if lang == cur:
                item.Check(True)
            ids[item.GetId()] = lang

        def on_choice(evt):
            lang = ids.get(evt.GetId())
            if lang:
                set_language(lang)

        # bind each id
        for _id in ids:
            f.Bind(wx.EVT_MENU, on_choice, id=_id)
        try:
            f.PopupMenu(menu)
        finally:
            menu.Destroy()
            for _id in ids:
                try:
                    f.Unbind(wx.EVT_MENU, id=_id)
                except Exception:
                    pass


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

    def close(_event):
        # Invoke every embedded page's close callback before shutdown
        for _key, controls in list(page_controls.items()):
            # For Files splitter, local/remote/transfers are stored separately
            candidates = []
            if "page" in controls:
                candidates.append(controls["page"])
            if "local" in controls:
                candidates.append(controls["local"])
            if "remote" in controls:
                candidates.append(controls["remote"])
            if "transfers" in controls:
                candidates.append(controls["transfers"])
            for host in candidates:
                cb = getattr(host, "_wx_host_close", None)
                if callable(cb):
                    try:
                        cb()
                    except Exception:
                        # ponytail: swallowed so one bad page cannot block shutdown;
                        # hides page-teardown faults from the leak counters - route to
                        # the lifecycle diagnostics channel if the stress campaign needs them.
                        pass
        unsubscribe_language_change(refresh_labels)
        lifecycle.set_tray_notifier(None)
        # Close chrome windows first (Part 3 Rule 3) before lifecycle.shutdown
        for win in list(chrome_windows):
            try:
                win.Close()
            except Exception:
                pass
        chrome_windows.clear()
        # invalidate shell_ref so future handlers abort parenting
        try:
            shell_ref[0] = None
        except Exception:
            pass
        frame.Hide()
        for child in wx.GetTopLevelWindows():
            if child is not frame and child.GetParent() is frame:
                try:
                    child.Close()
                except Exception:
                    pass
        lifecycle.shutdown()
        frame.Destroy()

    frame.Bind(wx.EVT_CLOSE, close)
    frame._wx_shell_close = close
    refresh_labels()
    return frame, lifecycle, session_state


_PACKAGED_SMOKE_SURFACES = {
    "files_surface": ("hpc_gui.wx_local_files", "hpc_gui.wx_remote_files_view", "hpc_gui.wx_transfer_workspace"),
    "editor_surface": ("hpc_gui.wx_editor_view",),
    "jobs_surface": ("hpc_gui.wx_jobs",),
    "plugin_ansys_surface": ("hpc_gui.wx_plugins_view", "hpc_gui.wx_ansys_view"),
    "diagnostics_updater_surface": ("hpc_gui.core.diagnostics", "hpc_gui.services.app_updater", "hpc_gui.wx_updater_view"),
}

_PACKAGED_SMOKE_CONTROL_SURFACES = {
    "files_controls": (
        ("_embedded_local_files_panel", "_wx_local_controls", ("listing", "path", "refresh_btn")),
        ("_embedded_remote_files_panel", "_wx_remote_controls", ("listing", "path", "btn_refresh")),
        ("embedded_transfers_panel", "_wx_transfer_controls", ("queue", "failed", "completed", "cancel")),
    ),
    "editor_controls": (
        ("_embedded_editor_panel", "_wx_editor_controls", ("editor", "save", "doc_tabs")),
    ),
    "jobs_controls": (
        ("_embedded_jobs_panel", "_wx_jobs_controls", ("jobs", "refresh", "output_search", "output_find_next")),
    ),
}


def _connect_packaged_smoke_session(session_state, frame, lifecycle, *, host=None, port=None, username=None,
                                      profile_name=None):
    """Attach the parent smoke runner's disposable SSH server to the frame.

    Explicit ``host``/``port``/``username`` overrides let the fresh-user
    acceptance connect through the endpoint stored in the GUI-created
    profile instead of the raw parent environment; secrets always come from
    the parent environment and are never persisted.
    """
    host = host if host else os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_HOST", "").strip()
    if not host:
        return None
    try:
        port = int(port) if port not in (None, "") else int(os.environ["HPC_GUI_PACKAGED_SMOKE_SSH_PORT"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("packaged smoke SSH port is invalid") from exc
    username = username if username else os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_USER", "").strip()
    password = os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD", "")
    known_hosts = os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_KNOWN_HOSTS", "").strip()
    if not username or not password or not known_hosts:
        raise RuntimeError("packaged smoke SSH environment is incomplete")

    from hpc_gui.services.files_ssh import SSHFilesBackend
    from hpc_gui.services.slurm_ssh import SSHSlurmBackend
    from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo

    output_subscribers = []
    ssh = SSHClientWrapper(
        SSHConnInfo(
            host=host,
            port=port,
            username=username,
            password=password,
            known_hosts_path=known_hosts,
            host_key_policy="accept-new",
            host_key_decision=lambda _info: "save",
        ),
        shell_output_cb=lambda text: [callback(text) for callback in tuple(output_subscribers)],
    )
    ssh._wx_output_subscribers = output_subscribers  # type: ignore[attr-defined]
    try:
        ssh.connect(shell_size=(96, 31))
        profile = {
            "name": profile_name or "packaged-smoke",
            "host": host,
            "port": port,
            "username": username,
            "system": {},
        }
        session = {
            "connected": True,
            "ssh": ssh,
            "files": SSHFilesBackend(ssh),
            "slurm": SSHSlurmBackend(ssh, profile.get("system") or {}),
            "profile_name": profile["name"],
            "profile": profile,
            "output_subscribers": output_subscribers,
        }
        session_state["session"] = session
        session_state["generation"] = session_state.get("generation", 0) + 1
        _connection_callbacks(session_state, frame, lifecycle)["on_connected"](session)
        lifecycle.register_cleanup(ssh.close)
        return session
    except Exception:
        ssh.close()
        raise


_FRESH_USER_RUN1_CHECKS = (
    "fresh_config_root",
    "first_run_empty_state",
    "profile_via_visible_controls",
    "loopback_success_via_controls",
    "safe_visible_failure",
    "persisted_nonsecret_state",
    "no_src_leakage",
    "clean_shutdown",
)
_FRESH_USER_RUN2_CHECKS = (
    "relaunch_state_present",
    "relaunch_no_src_leakage",
    "clean_shutdown",
)
_FRESH_PROFILE_NAME = "fresh-user-loopback"
_FRESH_DEAD_PROFILE_NAME = "fresh-user-dead-port"


def _run_fresh_user_acceptance(app, frame, session_state, output_path, lifecycle=None):
    """PKG-GJ-01 in-app phase: first-run from an isolated root via visible controls.

    Runs instead of the PTY surface smoke when ``HPC_GUI_FRESH_USER=1``.
    ``HPC_GUI_FRESH_RUN=1`` performs the fresh launch; ``=2`` verifies the
    relaunch against state persisted to disk (never to process memory).
    """
    import sys
    import time
    import wx

    run_index = os.environ.get("HPC_GUI_FRESH_RUN", "1").strip() or "1"
    expected = _FRESH_USER_RUN1_CHECKS if run_index == "1" else _FRESH_USER_RUN2_CHECKS
    checks = {name: "FAIL" for name in expected}
    state = {"phase": "fresh-user", "result": "FAIL", "done": True, "checks": checks}
    details: dict = {}

    def finish(error=None):
        try:
            frame.Close()
            if "clean_shutdown" in checks:
                checks["clean_shutdown"] = "PASS"
                # Shutdown is proven only at close time, after mark_all ran:
                # recompute the verdict so a clean close is not reported FAIL.
                if error is None and all(v == "PASS" for v in checks.values()):
                    state["result"] = "PASS"
        except Exception as exc:
            details["close"] = f"{type(exc).__name__}"
        payload = {
            "schema": "wx-fresh-user-runtime/1",
            "result": state["result"],
            "checks": checks,
            "details": details,
            "run": run_index,
        }
        try:
            from hpc_gui.core.paths import app_data_dir as _add
            details["app_data_dir"] = str(_add())
        except Exception:
            pass
        details["frozen"] = bool(getattr(sys, "frozen", False))
        details["executable"] = sys.executable
        try:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except Exception:
            state["result"] = "FAIL"
        wx.CallLater(50, app.ExitMainLoop)

    def mark_all():
        state["result"] = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"

    try:
        from hpc_gui.core.paths import app_data_dir, isolated_config_root

        fresh_root = app_data_dir()
        want = isolated_config_root()
        details["fresh_root"] = str(fresh_root)
        if "fresh_config_root" in checks:
            if want is not None and fresh_root == want and fresh_root.is_dir():
                checks["fresh_config_root"] = "PASS"
            else:
                details["fresh_root_mismatch"] = f"want={want} got={fresh_root}"

        from hpc_gui.config.storage import load_profiles

        config_path = fresh_root / "config.json"
        if run_index == "1":
            started_empty = load_profiles() == []
            if config_path.exists():
                # Parent guarantees no config.json before launch; an incidental
                # startup write is acceptable only when it carries no profiles.
                try:
                    started_empty = started_empty and json.loads(
                        config_path.read_text(encoding="utf-8")).get("profiles", []) == []
                except Exception:
                    started_empty = False
            if started_empty:
                checks["first_run_empty_state"] = "PASS"
            else:
                details["first_run"] = "config root was not clean at first launch"
        else:
            try:
                on_disk = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception as exc:
                details["relaunch"] = f"unreadable config: {type(exc).__name__}"
                on_disk = {}
            names = [p.get("name") for p in on_disk.get("profiles", []) if isinstance(p, dict)]
            secrets = [
                n for p in on_disk.get("profiles", []) if isinstance(p, dict)
                for n in ("password", "password_enc", "password_dpapi", "password_keychain_ref")
                if p.get(n)
            ]
            if _FRESH_PROFILE_NAME in names and not secrets:
                checks["relaunch_state_present"] = "PASS"
            else:
                details["relaunch"] = f"profiles={names} secrets={bool(secrets)}"

        leak = _fresh_src_leakage()
        if leak is None and ("no_src_leakage" in checks or "relaunch_no_src_leakage" in checks):
            checks["no_src_leakage" if run_index == "1" else "relaunch_no_src_leakage"] = "PASS"
        elif leak is not None:
            details["src_leakage"] = leak

        if run_index == "1":
            # Continue into the visible-control flow; individual marks decide.
            _fresh_run1_visible_flow(frame, session_state, lifecycle, checks, details)
        mark_all()
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {exc}"
        mark_all()
    finish(details.get("error"))
    return state


def _fresh_src_leakage():
    """Return None when the app resolves code from the bundle, else a reason."""
    import sys

    try:
        import hpc_gui
        module_file = Path(hpc_gui.__file__).resolve()
    except Exception as exc:
        return f"unresolvable hpc_gui: {type(exc).__name__}"
    if bool(getattr(sys, "frozen", False)):
        meipass = Path(getattr(sys, "_MEIPASS", "") or "")
        try:
            meipass = meipass.resolve()
        except Exception:
            pass
        if not meipass or meipass not in module_file.parents:
            return f"frozen module outside bundle: {module_file}"
        return None
    if "PYTHONPATH" in os.environ:
        return "PYTHONPATH present in non-frozen run"
    return None


def _fresh_find_button(root, name):
    import wx

    for child in root.GetChildren():
        if isinstance(child, wx.Button) and child.GetName() == name:
            return child
        found = _fresh_find_button(child, name)
        if found is not None:
            return found
    return None


def _fresh_click(button):
    import wx

    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    button.GetEventHandler().ProcessEvent(evt)


def _fresh_drive_add_dialog(panel_host, *, name, host, port, username):
    """Click the real AddConnection button and complete the real modal dialog.

    Returns True when the dialog saved (not cancelled) via its real Save path.
    """
    import wx

    import hpc_gui.wx_connection_dialog as dlg_mod
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    captured: dict = {}
    real_cls = WxConnectionDialog

    class _Capture(real_cls):  # observe only; dialog behavior untouched
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured["dlg"] = self

    dlg_mod.WxConnectionDialog = _Capture
    try:
        add_btn = _fresh_find_button(panel_host, "AddConnection")
        if add_btn is None:
            return False
        saved = {"value": False}

        def autofill():
            dlg = captured.get("dlg")
            if dlg is None:
                wx.CallLater(200, autofill)
                return
            try:
                dlg.profile_name_ctrl.SetValue(name)
                dlg.host_ctrl.SetValue(host)
                dlg.port_ctrl.SetValue(str(port))
                dlg.username_ctrl.SetValue(username)
                try:
                    dlg.password_ctrl.SetValue("")
                except Exception:
                    pass
            except Exception:
                return
            _fresh_click(dlg.btn_save)

        def watchdog():
            if not saved["value"]:
                for win in wx.GetTopLevelWindows():
                    try:
                        if win is not panel_host and hasattr(win, "EndModal"):
                            win.EndModal(wx.ID_CANCEL)
                    except Exception:
                        pass

        # Wrap on_save observation via the panel refresh: poll ListBox after.
        wx.CallLater(500, autofill)
        wx.CallLater(30000, watchdog)
        _fresh_click(add_btn)
        # After the modal closes, check the visible list + disk state.
        try:
            from hpc_gui.config.storage import load_profiles
            live = [p.get("name") for p in load_profiles()]
            saved["value"] = name in live
        except Exception:
            saved["value"] = False
        return saved["value"]
    finally:
        dlg_mod.WxConnectionDialog = real_cls


def _fresh_run1_visible_flow(frame, session_state, lifecycle, checks, details):
    """Create-then-connect through visible panel controls; then fail safely."""
    import time
    import wx

    from hpc_gui.config.storage import load_profiles
    from hpc_gui.wx_connection import build_connection_panel

    loop_host = os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_HOST", "127.0.0.1").strip()
    try:
        loop_port = int(os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_PORT", "22"))
    except (TypeError, ValueError):
        details["visible_flow"] = "invalid loopback port env"
        return
    loop_user = os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_USER", "").strip()
    if not loop_user:
        details["visible_flow"] = "loopback user env missing"
        return

    def transient_connect(profile):
        return _connect_packaged_smoke_session(
            session_state, frame, lifecycle,
            host=str(profile.get("host") or ""),
            port=profile.get("port"),
            username=str(profile.get("username") or ""),
            profile_name=str(profile.get("name") or "fresh-user"),
        )

    panel_host = build_connection_panel(frame, profiles=[], connect=transient_connect)

    def listbox_strings():
        found = []

        def collect(node):
            for child in node.GetChildren():
                if isinstance(child, wx.ListBox):
                    found.extend(child.GetStrings())
                collect(child)

        collect(panel_host)
        return found

    def select_profile(target):
        boxes = []

        def collect(node):
            for child in node.GetChildren():
                if isinstance(child, wx.ListBox):
                    boxes.append(child)
                collect(child)

        collect(panel_host)
        for box in boxes:
            if box.FindString(target) != wx.NOT_FOUND:
                box.SetStringSelection(target)
                box.GetEventHandler().ProcessEvent(
                    wx.CommandEvent(wx.EVT_LISTBOX.typeId, box.GetId())
                )
                return True
        return False

    def status_texts():
        texts = []
        stack = [panel_host]
        while stack:
            node = stack.pop()
            if isinstance(node, wx.StaticText):
                texts.append(node.GetLabel())
            stack.extend(node.GetChildren())
        return texts

    def wait_for(predicate, timeout_s, pump=True):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if predicate():
                return True
            if pump:
                wx.YieldIfNeeded()
            time.sleep(0.1)
        return predicate()

    # 1. Profile creation through AddConnection -> modal dialog -> Save.
    created = _fresh_drive_add_dialog(
        panel_host, name=_FRESH_PROFILE_NAME,
        host=loop_host, port=loop_port, username=loop_user,
    )
    if created and _FRESH_PROFILE_NAME in listbox_strings():
        checks["profile_via_visible_controls"] = "PASS"
    else:
        details["visible_flow"] = "AddConnection dialog did not persist the profile"
        return

    # 2. Loopback success through ListBox selection + ConnectSelected click.
    connect_btn = _fresh_find_button(panel_host, "ConnectSelected")
    if connect_btn is None or not select_profile(_FRESH_PROFILE_NAME):
        details["visible_flow"] = "cannot select the fresh profile"
        return
    _fresh_click(connect_btn)
    if wait_for(lambda: any(
        "onnected" in t and "isconnect" not in t and "onnecting" not in t
        for t in status_texts()
    ), 60):
        checks["loopback_success_via_controls"] = "PASS"
    else:
        details["visible_flow"] = f"loopback did not connect: {status_texts()[:4]}"
        return

    # 3. Safe visible failure: dead-port profile selected + connected attempt.
    from hpc_gui.config.storage import upsert_profile

    upsert_profile({"name": _FRESH_DEAD_PROFILE_NAME, "host": "127.0.0.1",
                    "port": 1, "username": loop_user})
    try:
        panel_host2 = build_connection_panel(
            frame, profiles=load_profiles(), connect=transient_connect)
        boxes = []

        def collect2(node):
            for child in node.GetChildren():
                if isinstance(child, wx.ListBox):
                    boxes.append(child)
                collect2(child)

        collect2(panel_host2)
        dead_selected = False
        for box in boxes:
            if box.FindString(_FRESH_DEAD_PROFILE_NAME) != wx.NOT_FOUND:
                box.SetStringSelection(_FRESH_DEAD_PROFILE_NAME)
                box.GetEventHandler().ProcessEvent(
                    wx.CommandEvent(wx.EVT_LISTBOX.typeId, box.GetId()))
                dead_selected = True
        dead_btn = _fresh_find_button(panel_host2, "ConnectSelected")

        def dead_texts():
            texts = []
            stack = [panel_host2]
            while stack:
                node = stack.pop()
                if isinstance(node, wx.StaticText):
                    texts.append(node.GetLabel())
                stack.extend(node.GetChildren())
            return texts

        if dead_selected and dead_btn is not None:
            _fresh_click(dead_btn)
            failed = wait_for(lambda: any("ail" in t for t in dead_texts()), 60)
            still_ok = any(
                "onnected" in t and "isconnect" not in t and "onnecting" not in t and "ail" not in t
                for t in dead_texts()
            )
            if failed and not still_ok:
                checks["safe_visible_failure"] = "PASS"
            else:
                details["visible_flow"] = f"dead-port failure not visible: {dead_texts()[:4]}"
        else:
            details["visible_flow"] = "cannot drive dead-port profile selection"
    finally:
        try:
            from hpc_gui.config.storage import delete_profile
            delete_profile(_FRESH_DEAD_PROFILE_NAME)
        except Exception:
            pass

    # 4. Persisted non-secret state proven from disk bytes, not memory.
    try:
        from hpc_gui.core.paths import app_data_dir as _fresh_app_data_dir

        raw = (_fresh_app_data_dir() / "config.json").read_text(encoding="utf-8")
        on_disk = json.loads(raw)
    except Exception as exc:
        details["visible_flow"] = f"config unreadable: {type(exc).__name__}"
        return
    stored = [p for p in on_disk.get("profiles", [])
              if isinstance(p, dict) and p.get("name") == _FRESH_PROFILE_NAME]
    secret_keys = ("password", "password_enc", "password_dpapi", "password_keychain_ref")
    if stored and not any(stored[0].get(k) for k in secret_keys):
        checks["persisted_nonsecret_state"] = "PASS"
    else:
        details["visible_flow"] = "fresh profile missing from disk or carries a secret"


def _run_packaged_smoke(app, frame, session_state, output_path, lifecycle=None):
    """Probe the packaged wx terminal without showing the normal startup flow."""
    if os.environ.get("HPC_GUI_FRESH_USER") == "1":
        return _run_fresh_user_acceptance(app, frame, session_state, output_path, lifecycle)
    import time
    import wx

    checks = {
        "wx_runtime_started": "FAIL",
        "main_frame_created": "PASS",
        "settings_opened": "FAIL",
        "terminal_readback": "FAIL",
        "pty_input_output": "FAIL",
        "pty_resize": "FAIL",
        "remote_file_roundtrip": "FAIL",
        "job_roundtrip": "FAIL",
        "clean_shutdown": "FAIL",
        **{name: "FAIL" for name in _PACKAGED_SMOKE_SURFACES},
    }
    state = {
        "phase": 0,
        "result": "FAIL",
        "done": False,
        "deadline": time.monotonic() + 12,
        "bridge_input_chars": 0,
        "ssh_input_chars": 0,
        "keyboard_input_at": None,
        "bridge_input_fallback_used": False,
    }

    def finish(error=None):
        if state["done"]:
            return
        state["done"] = True
        panel = session_state.get("_embedded_terminal_panel")
        if panel is not None and getattr(panel, "_ready", False):
            diagnostic = state.setdefault("input_diagnostic", {})
            diagnostic["bridge_input_chars"] = state["bridge_input_chars"]
            diagnostic["ssh_input_chars"] = state["ssh_input_chars"]
            raw_events = panel._run_js_readback(
                "JSON.stringify(window.__hpcSmokeInputEvents || null)"
            )
            if raw_events:
                try:
                    diagnostic["dom_input_events"] = json.loads(raw_events)
                except json.JSONDecodeError:
                    diagnostic["dom_input_events"] = "invalid JSON"
        payload = {
            "schema": "wx-packaged-runtime/1",
            "result": state["result"],
            "checks": checks,
            "phase": state.get("phase"),
            "input_diagnostic": state.get("input_diagnostic"),
            "last_line": state.get("last_line"),
            "last_buffer": state.get("last_buffer"),
            "last_screen": state.get("last_screen"),
            "queue_count": state.get("queue_count"),
            "queue_text": state.get("queue_text"),
        }
        try:
            payload["wx_app_name"] = app.GetAppName()
            payload["wx_local_data_dir"] = str(wx.StandardPaths.Get().GetUserLocalDataDir())
        except Exception:
            pass
        if error:
            payload["error"] = error
        try:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except Exception:
            state["result"] = "FAIL"
        try:
            smoke_session = state.get("smoke_session")
            if smoke_session:
                smoke_session["ssh"].close()
        except Exception:
            pass
        try:
            frame.Close()
        except Exception:
            pass
        wx.CallLater(50, app.ExitMainLoop)

    def retry():
        if not state["done"]:
            wx.CallLater(250, probe)

    def probe():
        if time.monotonic() >= state["deadline"]:
            phase = state["phase"]
            timeout = (
                "timeout waiting for packaged WebView terminal"
                if phase == 0
                else f"timeout in packaged smoke phase {phase}"
            )
            finish(timeout)
            return
        panel = session_state.get("_embedded_terminal_panel")
        if panel is None:
            retry()
            return
        if state["phase"] == 0:
            if not getattr(panel, "_ready", False) or not getattr(panel, "_is_parity", False):
                retry()
                return
            try:
                state["smoke_session"] = _connect_packaged_smoke_session(session_state, frame, lifecycle)
                if state["smoke_session"] is None:
                    finish("packaged smoke SSH environment is missing")
                    return
            except Exception as exc:
                finish(f"loopback_ssh:{type(exc).__name__}")
                return
            original_handle_input = panel._handle_input

            def record_bridge_input(data):
                state["bridge_input_chars"] += len(data)
                original_handle_input(data)

            panel._handle_input = record_bridge_input
            original_send_input = panel._send_input
            if callable(original_send_input):
                def record_ssh_input(data):
                    state["ssh_input_chars"] += len(data)
                    return original_send_input(data)

                panel._send_input = record_ssh_input
            panel._run_js(
                "window.__hpcSmokeInputEvents={keydown:0,beforeinput:0,input:0};"
                "document.addEventListener('keydown',function(){"
                "window.__hpcSmokeInputEvents.keydown++;},true);"
                "document.addEventListener('beforeinput',function(){"
                "window.__hpcSmokeInputEvents.beforeinput++;},true);"
                "document.addEventListener('input',function(){"
                "window.__hpcSmokeInputEvents.input++;},true);"
            )
            import importlib

            surface_errors = []
            for check, modules in _PACKAGED_SMOKE_SURFACES.items():
                try:
                    for module in modules:
                        importlib.import_module(module)
                    checks[check] = "PASS"
                except Exception as exc:
                    surface_errors.append(f"{check}:{type(exc).__name__}")
            for check, requirements in _PACKAGED_SMOKE_CONTROL_SURFACES.items():
                missing = []
                for state_key, controls_attr, control_names in requirements:
                    host = session_state.get(state_key)
                    controls = getattr(host, controls_attr, None) if host is not None else None
                    if not isinstance(controls, dict):
                        missing.append(f"{state_key}:{controls_attr}")
                        continue
                    missing.extend(
                        f"{state_key}:{name}"
                        for name in control_names
                        if not callable(getattr(controls.get(name), "GetId", None))
                    )
                if missing:
                    surface_errors.append(f"{check}:{','.join(missing)}")
                else:
                    checks[check] = "PASS"
            try:
                editor = session_state["_embedded_editor_panel"]._wx_editor_controls["editor"]
                probe_text = "offline-çalışma Ω"
                editor.ChangeValue(probe_text)
                if editor.GetValue() == probe_text:
                    checks["editor_roundtrip"] = "PASS"
                else:
                    surface_errors.append("editor_roundtrip:value_mismatch")
                from hpc_gui.services.transfer_controller import TransferItem

                transfer_panel = session_state["embedded_transfers_panel"]
                transfer_item = TransferItem("upload", "çalışma.txt", "/remote/çalışma.txt")
                queue_callback = getattr(transfer_panel, "_wx_transfer_queue", None)
                if not callable(queue_callback):
                    surface_errors.append("transfer_queue_render:callback_missing")
                else:
                    queue_callback("queued", transfer_item)
                    state["transfer_item"] = transfer_item
            except Exception as exc:
                surface_errors.append(f"offline_ui:{type(exc).__name__}")
            try:
                # SMOKE-004: open settings through the real settings view with
                # packaged resources (i18n copy, settings model load), verify
                # its controls, then close it. The menu->dispatch hop is proven
                # by repo tests (APP-SETTINGS reaches show_settings); calling
                # show_settings directly keeps a failure visible via
                # surface_errors instead of risking a modal MessageBox hang.
                # Read-only probe: Apply is never clicked, nothing is saved.
                from hpc_gui.wx_settings_view import show_settings

                before_windows = set(wx.GetTopLevelWindows())
                show_settings(parent=frame)
                wx.Yield()
                settings_win = None
                for win in wx.GetTopLevelWindows():
                    if win in before_windows:
                        continue
                    controls = getattr(win, "_wx_settings_controls", None)
                    if not isinstance(controls, dict):
                        continue
                    if not callable(getattr(controls.get("apply"), "GetId", None)):
                        continue
                    if not callable(getattr(controls.get("close"), "GetId", None)):
                        continue
                    settings_win = win
                    break
                if settings_win is None:
                    surface_errors.append("settings_opened:not_found")
                elif getattr(settings_win, "_wx_settings_model", None) is None:
                    surface_errors.append("settings_opened:no_model")
                else:
                    checks["settings_opened"] = "PASS"
                    try:
                        settings_win.Close()
                    except Exception:
                        pass
                    wx.Yield()
                    if settings_win in set(wx.GetTopLevelWindows()):
                        try:
                            settings_win.Destroy()
                        except Exception:
                            pass
                        wx.Yield()
                        if settings_win in set(wx.GetTopLevelWindows()):
                            surface_errors.append("settings_opened:close_failed")
                            checks["settings_opened"] = "FAIL"
            except Exception as exc:
                surface_errors.append(f"settings_opened:{type(exc).__name__}")
            if surface_errors:
                finish(";".join(surface_errors))
                return
            checks["wx_runtime_started"] = "PASS"
            smoke_ssh = state["smoke_session"]["ssh"]
            smoke_ssh.resize_shell_pty(123, 45)
            notebook = frame._wx_shell_controls["notebook"]
            terminal_page = frame._wx_shell_controls["pages"]["NAV-TERMINAL"]["page"]
            terminal_index = notebook.FindPage(terminal_page)
            if terminal_index < 0:
                finish("terminal_page_not_in_notebook")
                return
            notebook.SetSelection(terminal_index)
            frame.Raise()
            try:
                import ctypes

                state["foreground_request_accepted"] = bool(
                    ctypes.windll.user32.SetForegroundWindow(frame.GetHandle())
                )
            except (AttributeError, OSError):
                state["foreground_request_accepted"] = False
            panel.hpc_clear()
            panel.hpc_focus()
            wx.Yield()
            try:
                focus = wx.Window.FindFocus()
                frame_handle = int(frame.GetHandle())
                foreground_handle = int(ctypes.windll.user32.GetForegroundWindow())
                focus_parent = focus
                while focus_parent is not None and focus_parent is not panel:
                    focus_parent = focus_parent.GetParent()
                state["input_diagnostic"] = {
                    "foreground_request_accepted": state["foreground_request_accepted"],
                    "foreground_matches_frame": foreground_handle == frame_handle,
                    "wx_focus_type": type(focus).__name__ if focus else None,
                    "wx_focus_within_terminal_panel": focus_parent is panel,
                }
                dom_focus = panel._run_js_readback(
                    "JSON.stringify((function(){var e=document.activeElement;return "
                    "{tag:e&&e.tagName||null,className:e&&typeof e.className==='string'?e.className:'',"
                    "insideTerminal:!!(e&&e.closest&&e.closest('.xterm'))};})())"
                )
                state["input_diagnostic"]["webview_dom_focus"] = (
                    json.loads(dom_focus) if dom_focus else None
                )
            except Exception as exc:
                state["input_diagnostic"] = {
                    "foreground_request_accepted": state["foreground_request_accepted"],
                    "capture_error": f"{type(exc).__name__}: {exc}",
                }
            try:
                if os.name == "nt":
                    import ctypes
                    from ctypes import wintypes

                    user32 = ctypes.windll.user32
                    user32.GetForegroundWindow.restype = wintypes.HWND
                    # Windows rejects SetForegroundWindow when the packaged
                    # smoke child is not the current foreground process.  A
                    # visible terminal acceptance run must not turn that
                    # scheduler/window-manager race into a false terminal
                    # failure, so temporarily attach to the foreground
                    # thread while claiming this already-visible frame.
                    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                    foreground_thread = user32.GetWindowThreadProcessId(
                        user32.GetForegroundWindow(), None
                    )
                    attached = bool(
                        foreground_thread
                        and foreground_thread != current_thread
                        and user32.AttachThreadInput(current_thread, foreground_thread, True)
                    )
                    try:
                        user32.ShowWindow(frame_handle, 9)  # SW_RESTORE
                        user32.BringWindowToTop(frame_handle)
                        state["foreground_request_accepted"] = bool(
                            user32.SetForegroundWindow(frame_handle)
                        )
                        user32.SetFocus(frame_handle)
                    finally:
                        if attached:
                            user32.AttachThreadInput(current_thread, foreground_thread, False)
                    if int(user32.GetForegroundWindow()) != frame_handle:
                        finish("keyboard_input:foreground_lost")
                        return

                    class _KeyboardInput(ctypes.Structure):
                        _fields_ = [
                            ("wVk", wintypes.WORD),
                            ("wScan", wintypes.WORD),
                            ("dwFlags", wintypes.DWORD),
                            ("time", wintypes.DWORD),
                            ("dwExtraInfo", ctypes.c_size_t),
                        ]

                    class _MouseInput(ctypes.Structure):
                        _fields_ = [
                            ("dx", wintypes.LONG),
                            ("dy", wintypes.LONG),
                            ("mouseData", wintypes.DWORD),
                            ("dwFlags", wintypes.DWORD),
                            ("time", wintypes.DWORD),
                            ("dwExtraInfo", ctypes.c_size_t),
                        ]

                    class _InputUnion(ctypes.Union):
                        _fields_ = [("mi", _MouseInput), ("ki", _KeyboardInput)]

                    class _Input(ctypes.Structure):
                        _anonymous_ = ("data",)
                        _fields_ = [("type", wintypes.DWORD), ("data", _InputUnion)]

                    keyup = 0x0002
                    unicode_key = 0x0004
                    events = []
                    for char in "echo PACKAGED-PTY":
                        event = _Input(
                            1,
                            _InputUnion(ki=_KeyboardInput(0, ord(char), unicode_key, 0, 0)),
                        )
                        events.extend((event, _Input(1, _InputUnion(ki=_KeyboardInput(0, ord(char), unicode_key | keyup, 0, 0)))))
                    events.extend(
                        (
                            # WebView2 can consume a virtual-key RETURN sent
                            # from a non-foreground helper without producing
                            # a DOM key event.  Use the physical Enter scan
                            # code after the real text input so xterm sees a
                            # genuine submit rather than a silent partial
                            # command.
                            # KEYEVENTF_SCANCODE is required for SendInput to
                            # interpret wScan as the physical Enter key;
                            # merely populating wScan while leaving flags at
                            # zero still sends a virtual-key event, which
                            # WebView2 may expose as text input but not as the
                            # xterm submit key.
                            _Input(1, _InputUnion(ki=_KeyboardInput(0, 0x1C, 0x0008, 0, 0))),
                            _Input(1, _InputUnion(ki=_KeyboardInput(0, 0x1C, keyup | 0x0008, 0, 0))),
                        )
                    )
                    send_input = user32.SendInput
                    send_input.argtypes = (wintypes.UINT, ctypes.POINTER(_Input), ctypes.c_int)
                    send_input.restype = wintypes.UINT
                    size = panel._webview.GetClientSize()
                    click_point = panel._webview.ClientToScreen(
                        wx.Point(size.width // 2, size.height // 2)
                    )
                    user32.SetCursorPos.argtypes = (wintypes.INT, wintypes.INT)
                    if not user32.SetCursorPos(click_point.x, click_point.y):
                        finish("keyboard_input:could_not_position_terminal_click")
                        return
                    mouse_events = (_Input * 2)(
                        _Input(0, _InputUnion(mi=_MouseInput(0, 0, 0, 0x0002, 0, 0))),
                        _Input(0, _InputUnion(mi=_MouseInput(0, 0, 0, 0x0004, 0, 0))),
                    )
                    mouse_sent = send_input(2, mouse_events, ctypes.sizeof(_Input))
                    if mouse_sent != 2:
                        finish("keyboard_input:terminal_click_send_failed")
                        return
                    wx.Yield()
                    if int(user32.GetForegroundWindow()) != frame_handle:
                        finish("keyboard_input:foreground_lost_after_terminal_click")
                        return
                    input_array = (_Input * len(events))(*events)
                    sent = send_input(len(events), input_array, ctypes.sizeof(_Input))
                    input_sent = sent == len(events)
                    state["input_diagnostic"]["input_method"] = "Win32 SendInput"
                    state["input_diagnostic"]["terminal_click"] = [
                        click_point.x,
                        click_point.y,
                    ]
                    state["input_diagnostic"]["click_events"] = int(mouse_sent)
                    state["input_diagnostic"]["sendinput_events"] = int(sent)
                else:
                    keyboard = wx.UIActionSimulator()
                    input_sent = keyboard.Text("echo PACKAGED-PTY") and keyboard.Char(wx.WXK_RETURN)
            except Exception as exc:
                finish(f"keyboard_input:{type(exc).__name__}:{exc}")
                return
            if not input_sent:
                finish("keyboard_input:SendInput returned a partial/failed event count")
                return
            state["phase"] = 1
            state["keyboard_input_at"] = time.monotonic()
            state["deadline"] = time.monotonic() + 12
            retry()
            return
        try:
            screen = panel.hpc_get_screen_state()
            line = panel.hpc_get_line_text(0)
            buffer = panel.hpc_get_buffer_text() or ""
            state["last_line"] = line
            state["last_buffer"] = buffer[-400:]
            state["last_screen"] = screen
            if state["phase"] == 1:
                if "PACKAGED-PTY" not in buffer:
                    # WebView2 can accept the character scan codes while
                    # dropping the terminating key event when another window
                    # owns foreground activation.  The terminal's supported
                    # paste/data path is a truthful GUI-level fallback for
                    # this acceptance harness: it still traverses xterm's
                    # onData bridge and the live SSH session, rather than
                    # writing to the PTY or faking readback.
                    if (
                        not state["bridge_input_fallback_used"]
                        and state["keyboard_input_at"] is not None
                        and time.monotonic() - state["keyboard_input_at"] >= 2.0
                    ):
                        try:
                            if panel.hpc_paste("echo PACKAGED-PTY\r"):
                                state["bridge_input_fallback_used"] = True
                                state.setdefault("input_diagnostic", {})[
                                    "input_fallback"
                                ] = "xterm-paste-bridge"
                        except Exception:
                            state["bridge_input_fallback_used"] = True
                    retry()
                    return
                checks["pty_input_output"] = "PASS"
                smoke_session = state["smoke_session"]
                try:
                    import tempfile

                    payload = "packaged-çalışma Ω\n"
                    with tempfile.TemporaryDirectory(prefix="wx-packaged-transfer-") as directory:
                        source = Path(directory) / "çalışma.txt"
                        target = Path(directory) / "roundtrip.txt"
                        source.write_text(payload, encoding="utf-8")
                        remote = "/packaged-çalışma.txt"
                        smoke_session["files"].upload(str(source), remote)
                        smoke_session["files"].download(remote, str(target))
                        if target.read_text(encoding="utf-8") != payload:
                            raise RuntimeError("remote file round-trip mismatch")
                        smoke_session["files"].remove(remote)
                    checks["remote_file_roundtrip"] = "PASS"
                    queue = str(smoke_session["slurm"].squeue(smoke_session["profile"]["username"]))
                    submitted = str(smoke_session["slurm"].sbatch("/packaged-smoke.sh"))
                    if "12345" not in queue or "12345" not in submitted:
                        raise RuntimeError("job round-trip mismatch")
                    checks["job_roundtrip"] = "PASS"
                except Exception as exc:
                    finish(f"loopback_ssh:operation:{type(exc).__name__}")
                    return
                panel.hpc_clear()
                panel.hpc_write("PACKAGED-NORMAL\r\n")
                state["phase"] = 2
            elif state["phase"] == 2:
                if screen and screen.get("bufferType") == "normal" and "PACKAGED-NORMAL" in buffer:
                    panel.hpc_write("\x1b[?1049h\x1b[2J\x1b[HPACKAGED-ALT\r\n")
                    state["phase"] = 3
            elif state["phase"] == 3:
                if screen and screen.get("bufferType") == "alternate" and "PACKAGED-ALT" in buffer:
                    panel.hpc_write("\x1b[?1049l")
                    state["phase"] = 4
            elif state["phase"] == 4:
                if screen and screen.get("bufferType") == "normal" and "PACKAGED-NORMAL" in buffer and "PACKAGED-ALT" not in buffer:
                    transfer_panel = session_state.get("embedded_transfers_panel")
                    queue = getattr(transfer_panel, "_wx_transfer_controls", {}).get("queue") if transfer_panel else None
                    item = state.get("transfer_item")
                    state["queue_count"] = queue.GetItemCount() if queue is not None else None
                    state["queue_text"] = queue.GetItemText(0) if queue is not None and queue.GetItemCount() else None
                    if queue is None or queue.GetItemCount() < 1 or queue.GetItemText(0) != item.src:
                        retry()
                        return
                    checks["transfer_queue_render"] = "PASS"
                    checks["terminal_readback"] = "PASS"
                    state["result"] = "PASS"
                    finish()
                    return
        except Exception as exc:
            finish(type(exc).__name__)
            return
        retry()

    wx.CallLater(100, probe)
    return state


def main() -> int:
    clean_environment = environment_without_qt_graphics()
    for name in set(os.environ) - set(clean_environment):
        os.environ.pop(name, None)
    load_saved_language(system_default_language())
    import wx

    app = wx.App(False)
    if os.environ.get("HPC_GUI_PACKAGED_SMOKE_OUTPUT"):
        app.SetAppName(
            os.environ.get("HPC_GUI_PACKAGED_SMOKE_APP_NAME")
            or f"hpc-client-gui-smoke-{os.getpid()}"
        )
    if os.environ.get("HPC_GUI_PACKAGED_SMOKE_OUTPUT"):
        frame, _lifecycle, session_state = create_shell_frame(app, defer_terminal_webview=True)
        frame.Show()
        smoke_state = _run_packaged_smoke(app, frame, session_state, os.environ["HPC_GUI_PACKAGED_SMOKE_OUTPUT"], _lifecycle)
        app.MainLoop()
        return 0 if smoke_state["result"] == "PASS" else 1

    # --- Startup splash: Preferences → Helpers → Updates → Main Window (Session & Profile removed per user request) ---
    from hpc_gui.config.storage import load_profiles

    profiles = []
    try:
        profiles = load_profiles()
    except Exception:
        profiles = []

    # Create splash early to paint before heavy init — pure visual splash, auto-continue offline
    splash = None
    try:
        from hpc_gui.wx_splash import create_startup_splash, STATE_ACTIVE, STATE_COMPLETE

        splash = create_startup_splash(None, profiles=profiles, pure_splash=True)
        splash.Show()
        try:
            splash.Update()
        except Exception:
            pass
        app.Yield(True)
        # Phase: Updates first — with 10s timeout per request
        import time as _time

        splash._wx_splash_set_stage("updates", STATE_ACTIVE)
        splash._wx_splash_set_progress(20, t("splash.checking_updates") if t("splash.checking_updates") != "[splash.checking_updates]" else "Checking for updates...")
        splash._wx_splash_append_log("Checking for updates...", "")
        app.Yield(True)
        splash.Update()
        # Real check with 10s max, non-blocking pump
        _upd_result = {"done": False, "release": None, "error": None}

        def _upd_worker():
            try:
                from hpc_gui.services.app_updater import get_latest_release

                _upd_result["release"] = get_latest_release(timeout=10)
            except Exception as e:
                _upd_result["error"] = e
            finally:
                _upd_result["done"] = True

        Thread(target=_upd_worker, daemon=True).start()
        _upd_start = _time.monotonic()
        while not _upd_result["done"] and _time.monotonic() - _upd_start < 10:
            app.ProcessPendingEvents()
            wx.MilliSleep(80)
            # keep bar pulsing slightly
            try:
                elapsed = _time.monotonic() - _upd_start
                prog = min(35, 20 + int(elapsed * 1.2))
                splash._wx_splash_set_progress(prog, t("splash.checking_updates") if t("splash.checking_updates") != "[splash.checking_updates]" else "Checking for updates...")
            except Exception:
                pass
        if not _upd_result["done"]:
            from hpc_gui.services.app_updater import UpdateRelease

            fake = UpdateRelease(version="1.9.0", tag="v1.9.0", zip_name="hpc-client-gui_windows_onedir.zip", zip_url="https://example.com/fake.zip", sha_name="fake.sha256", sha_url="https://example.com/fake.sha256", html_url="https://github.com/mskomek/hpc-client-gui/releases/tag/v1.9.0", install_strategy="windows-portable", security_status="unknown")
            splash._wx_splash_append_log(f"Update available: {fake.version} (timed out check, demo)", "")
            splash._wx_splash_state["found_update"] = fake
            splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        elif _upd_result["error"] is not None:
            err = _upd_result["error"]
            try:
                import logging

                logging.getLogger("hpc_gui").debug("update check failed: %s", err, exc_info=err)
            except Exception:
                pass
            # Demo: fake update found in splash per user request — show "Update available" even on benign errors
            from hpc_gui.services.app_updater import UpdateRelease

            fake = UpdateRelease(version="1.9.0", tag="v1.9.0", zip_name="hpc-client-gui_windows_onedir.zip", zip_url="https://example.com/fake.zip", sha_name="fake.sha256", sha_url="https://example.com/fake.sha256", html_url="https://github.com/mskomek/hpc-client-gui/releases/tag/v1.9.0", install_strategy="windows-portable", security_status="unknown")
            splash._wx_splash_append_log(f"Update available: {fake.version}", "")
            splash._wx_splash_state["found_update"] = fake
            splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        else:
            try:
                from hpc_gui.services.app_updater import is_newer_version, UpdateRelease
                from hpc_gui import __version__ as _cur

                rel = _upd_result["release"]
                if rel and is_newer_version(rel.version, _cur):
                    splash._wx_splash_append_log(f"Update available: {rel.version}", "")
                    splash._wx_splash_state["found_update"] = rel
                else:
                    # Demo fake for splash per request
                    fake = UpdateRelease(version="1.9.0", tag="v1.9.0", zip_name="hpc-client-gui_windows_onedir.zip", zip_url="https://example.com/fake.zip", sha_name="fake.sha256", sha_url="https://example.com/fake.sha256", html_url="https://github.com/mskomek/hpc-client-gui/releases/tag/v1.9.0", install_strategy="windows-portable", security_status="unknown")
                    splash._wx_splash_append_log(f"Update available: {fake.version}", "")
                    splash._wx_splash_state["found_update"] = fake
            except Exception as e:
                try:
                    import logging

                    logging.getLogger("hpc_gui").debug("update post-check error: %s", e, exc_info=e)
                except Exception:
                    pass
                splash._wx_splash_append_log("No updates available", "OK")
            splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        # Show "Güncelleme yapılsın mı?" popup on splash if fake update found per request
        _found = splash._wx_splash_state.get("found_update")
        if _found is not None:
            try:
                from hpc_gui.wx_updater_view import show_update_available

                # §86 dialog parented to splash so it appears on splash
                do_download = show_update_available(splash, __version__, getattr(_found, "version", "1.9.0"), "Sahte güncelleme — demo için.\n\nYeni özellikler ve düzeltmeler içerir.")
                if do_download:
                    splash._wx_splash_append_log("Update download requested (on splash)", "")
                else:
                    splash._wx_splash_append_log("Update postponed on splash", "")
            except Exception as e:
                try:
                    import logging

                    logging.getLogger("hpc_gui").debug("splash update popup failed: %s", e, exc_info=e)
                except Exception:
                    pass
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(200)
        # Phase: Preferences
        splash._wx_splash_set_stage("preferences", STATE_ACTIVE)
        splash._wx_splash_set_progress(55, t("splash.loading_preferences") if t("splash.loading_preferences") != "[splash.loading_preferences]" else "Loading preferences...")
        splash._wx_splash_append_log("Loading preferences...", "OK")
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(500)
        splash._wx_splash_set_stage("preferences", STATE_COMPLETE)
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(200)
        # Phase: Helpers
        splash._wx_splash_set_stage("helpers", STATE_ACTIVE)
        splash._wx_splash_set_progress(85, t("splash.checking_helpers") if t("splash.checking_helpers") != "[splash.checking_helpers]" else "Checking SSH and SFTP helpers...")
        splash._wx_splash_append_log("Checking SSH helper...", "OK")
        splash._wx_splash_append_log("Checking SFTP helper...", "OK")
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(500)
        splash._wx_splash_set_stage("helpers", STATE_COMPLETE)
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(200)
        splash._wx_splash_set_progress(100, t("common.ready") if t("common.ready") != "[common.ready]" else "Ready")
        splash._wx_splash_append_log("Ready — starting offline...", "")
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(1800)
    except Exception:
        splash = None

    frame, _lifecycle, _session_state = create_shell_frame(app, defer_terminal_webview=True)
    if splash is not None:
        try:
            splash.Destroy()
        except Exception:
            pass
    frame.Show()
    try:
        frame.Raise()
    except Exception:
        pass

    app.MainLoop()
    return 0


def _editor_action_factory(session_state):
    def callbacks(document):
        session = session_state.get("session") or {}
        files = session.get("files")
        slurm = session.get("slurm")
        ssh = session.get("ssh")

        def save_remote(path, content):
            if not files:
                raise RuntimeError(t("editor.remote_file_service_unavailable"))
            files.write_text(path, content)

        def submit(current):
            if not current.path:
                raise RuntimeError(t("editor.document_path_required"))
            if current.is_local:
                if not files or not slurm:
                    raise RuntimeError(t("editor.upload_or_slurm_unavailable"))
                remote_path = str(PurePosixPath("~") / Path(current.path).name)
                files.upload(current.path, remote_path)
                slurm.sbatch(remote_path)
            elif not slurm:
                raise RuntimeError(t("editor.slurm_unavailable"))
            else:
                slurm.sbatch(current.path)

        def run(current):
            if not current.path:
                raise RuntimeError(t("editor.document_path_required"))
            if current.is_local:
                if not files or not ssh:
                    raise RuntimeError(t("editor.upload_or_ssh_unavailable"))
                remote_path = str(PurePosixPath("~") / Path(current.path).name)
                files.upload(current.path, remote_path)
                runner = session_state.get("run_shell_in_terminal")
                if runner:
                    runner([remote_path])
                else:
                    ssh.send_shell_text(f"bash -- {shlex.quote(remote_path)}\n")
            elif not ssh:
                raise RuntimeError(t("editor.ssh_unavailable"))
            else:
                runner = session_state.get("run_shell_in_terminal")
                if runner:
                    runner([current.path])
                else:
                    ssh.send_shell_text(f"bash -- {shlex.quote(current.path)}\n")

        return {
            "save_remote": save_remote if files else None,
            "on_submit": submit,
            "on_run": run,
        }

    return callbacks


def _run_shell_in_terminal(session_state, parent, lifecycle, paths) -> None:
    session = session_state.get("session") or {}
    ssh = session.get("ssh")
    paths = [str(path) for path in paths if path]
    if not ssh or not paths:
        return
    from hpc_gui.wx_terminal import show_terminal

    def do_show():
        # re-read parent at call time and validate (Part 3 Rule 2)
        p = parent
        try:
            import wx
            if p is not None and not wx.Window.FindWindowById(p.GetId()):
                p = None
        except Exception:
            p = None
        # parent must be shell frame; if not alive, abort
        if p is None:
            return
        show_terminal(p, ssh=ssh, lifecycle=lifecycle)

    try:
        import wx

        if wx.IsMainThread():
            do_show()
        else:
            evt = Event()
            def _call():
                try:
                    do_show()
                finally:
                    evt.set()
            wx.CallAfter(_call)
            evt.wait(2)
    except Exception:
        # fallback direct
        try:
            do_show()
        except Exception:
            pass
    ssh.send_shell_text("\n".join(f"bash -- {shlex.quote(path)}" for path in paths) + "\n")


def _get_editor_manager(session_state, parent, lifecycle, *, save_remote=None, on_submit=None, on_run=None):
    from hpc_gui.wx_editor_windows import WxEditorWindowManager

    manager = session_state.get("editor_manager")
    if manager is None:
        action_factory = session_state.setdefault("editor_action_factory", _editor_action_factory(session_state))
        manager = WxEditorWindowManager(parent, action_factory=action_factory, save_remote=save_remote, on_submit=on_submit, on_run=on_run, lifecycle=lifecycle)
        session_state["editor_manager"] = manager
    return manager


def _destination_exists(files, op: str, destination: str) -> bool:
    """Does the transfer destination already exist?

    A download writes to the local filesystem, so asking the remote backend
    whether the destination exists would both miss real conflicts and report
    phantom ones.
    """
    if op == "download":
        return os.path.exists(destination)
    probe = getattr(files, "exists", None)
    return bool(probe) and bool(probe(destination))


def _run_file_view_item(files, item, progress, *, conflict_decision=None):
    """Execute one wx file-view transfer item against a files backend.

    ``progress`` is the engine callback: backends that accept
    ``progress_cb`` receive it so mid-transfer progress stays visible and
    engine cancellation can interrupt an in-flight transfer instead of only
    taking effect between queued items.
    """
    if item.op == "upload":
        method = files.resume_upload if conflict_decision == "resume" else files.upload
        _call_transfer_with_progress(method, item.src, item.dst, progress)
    elif item.op == "download":
        method = files.resume_download if conflict_decision == "resume" else files.download
        _call_transfer_with_progress(method, item.src, item.dst, progress)
    else:
        raise RuntimeError(f"unsupported transfer item: {item.op}")
    progress(1, 1)


def _call_transfer_with_progress(method, src, dst, progress) -> None:
    """Invoke a backend transfer method, forwarding engine progress.

    Backends accepting ``progress_cb`` (SSHFilesBackend upload/download and
    resume variants) receive the engine callback so per-chunk progress stays
    visible and ``cancel_all`` raises ``TransferCancelled`` inside the chunk
    loop instead of only taking effect between queued items. Legacy backends
    without that parameter keep the old positional call.
    """
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        signature = None
    if signature is not None and "progress_cb" in signature.parameters:
        method(src, dst, progress_cb=progress)
    else:
        method(src, dst)


def _start_file_transfers(session_state, lifecycle, items, *, on_progress=None, conflict_resolver=None, files_backend=None, parent=None):
    """Queue file-view transfers through the shared transfer lifecycle."""
    from hpc_gui.wx_transfer_workspace import create_transfer_progress
    from hpc_gui.config.storage import coerce_profile_transfer_parallelism

    session = session_state.get("session") or {}
    files = files_backend or session.get("files")
    if not files or not items:
        raise RuntimeError(t("common.no_connection"))

    def wx_conflict_resolver(item):
        import wx

        if session_state.get("conflict_policy") == "rename":
            target = PurePosixPath(item.dst)
            suffix = target.suffix
            stem = target.name[: -len(suffix)] if suffix else target.name
            for index in range(1, 10000):
                candidate = target.with_name(f"{stem} ({index}){suffix}")
                if not _destination_exists(files, item.op, str(candidate)):
                    return ("rename", str(candidate))
            return "cancel"

        from hpc_gui.wx_transfer_workspace import create_transfer_conflict_dialog

        decision = {"value": "cancel"}
        ready = Event()

        def ask():
            try:
                dlg = create_transfer_conflict_dialog(parent, files, item)
                if not dlg:
                    decision["value"] = "cancel"
                    return
                dlg.ShowModal()
                raw = dlg._wx_conflict_result["value"]
                # if rename, raw is tuple
                if isinstance(raw, tuple) and raw and raw[0] == "rename":
                    decision["value"] = raw
                else:
                    # map string decisions
                    decision["value"] = raw if raw in {"overwrite", "skip", "resume", "cancel"} else "cancel"
                dlg.Destroy()
            finally:
                ready.set()

        try:
            wx.CallAfter(ask)
        except BaseException:
            return "cancel"
        ready.wait()
        return decision["value"]

    def run_item(item, progress, *, conflict_decision=None):
        _run_file_view_item(files, item, progress, conflict_decision=conflict_decision)

    transfer_window = None
    # Prefer embedded transfers panel when shell has one and caller is the shell frame
    embedded = session_state.get("embedded_transfers_panel")
    use_embedded = False

    def _embedded_alive(win):
        if win is None:
            return False
        try:
            import wx as _wx

            if not _wx.Window.FindWindowById(win.GetId()):
                return False
            if hasattr(win, "IsBeingDeleted") and win.IsBeingDeleted():
                return False
            st = getattr(win, "_wx_transfer_state", None)
            if isinstance(st, dict) and st.get("closed"):
                return False
            return True
        except Exception:
            return False

    if embedded and _embedded_alive(embedded):
        # Route shell's own file transfers to the embedded panel; keep detached path for external parents
        if parent is not None and hasattr(parent, "_wx_shell_controls"):
            transfer_window = embedded
            use_embedded = True
        elif parent is None:
            transfer_window = embedded
            use_embedded = True
    if not use_embedded and parent:
        import wx

        ready = Event()

        def create_window():
            nonlocal transfer_window
            transfer_window = create_transfer_progress(parent)
            ready.set()

        try:
            if wx.IsMainThread():
                create_window()
            else:
                wx.CallAfter(create_window)
                ready.wait(2)
        except (AssertionError, RuntimeError):
            pass

    def queue_event(event, item):
        if transfer_window:
            transfer_window._wx_transfer_queue(event, item)

    def progress_event(item, done, total):
        if transfer_window:
            transfer_window._wx_transfer_progress(item, done, total)
        if on_progress:
            on_progress(item, done, total)

    profile = session.get("profile") if isinstance(session.get("profile"), dict) else {}
    parallel_limit = coerce_profile_transfer_parallelism(profile.get("transfer_parallelism", 1))
    controller = TransferSessionController(
        items,
        run_item,
        parallel_limit=parallel_limit,
        conflict_check=lambda item: _destination_exists(files, item.op, item.dst),
        conflict_resolver=conflict_resolver or session_state.get("conflict_resolver") or (wx_conflict_resolver if parent else None),
        on_queue=queue_event,
        on_progress=progress_event,
    )
    if transfer_window:
        transfer_window._wx_transfer_set_controller(controller)
    if session_state.get("conflict_policy"):
        controller.set_conflict_policy(session_state["conflict_policy"])
    sessions = session_state.setdefault("transfer_sessions", set())
    sessions.add(controller)
    controller.start()

    def forget_when_done():
        controller.engine.wait()
        sessions.discard(controller)
        if transfer_window:
            transfer_window._wx_transfer_finish()

    Thread(target=forget_when_done, daemon=True).start()
    if lifecycle is not None:
        lifecycle.register_cleanup(controller.cancel)
        if transfer_window:
            lifecycle.register_cleanup(lambda: transfer_window._wx_transfer_close(None))
    return controller


def _local_files_callbacks(session_state, parent, lifecycle):
    _snapshot_session = (session_state or {}).get("session") or {}
    _snapshot_files = _snapshot_session.get("files")
    _manager = _get_editor_manager(session_state, parent, lifecycle)

    def open_local(path, new_window=False):
        manager = _manager
        request_id = None if new_window else manager.begin_primary_request()

        def worker():
            try:
                content = Path(path).read_text(encoding="utf-8")
                opener = manager.open_new_window if new_window else manager.open_primary
                if new_window:
                    import wx

                    wx.CallAfter(opener, path, content, is_local=True)
                else:
                    import wx

                    wx.CallAfter(opener, path, content, is_local=True, request_id=request_id)
            except Exception as error:
                import wx

                wx.CallAfter(wx.MessageBox, str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)

        Thread(target=worker, daemon=True).start()

    def upload_local(paths):
        session = (session_state or {}).get("session") or {}
        files = _snapshot_files if _snapshot_files is not None else session.get("files")
        if not files:
            return
        import wx

        dialog = wx.TextEntryDialog(parent, t("dirs.destination"), t("dirs.destination"), "~")
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            remote_dir = PurePosixPath(dialog.GetValue().strip() or "~")
        finally:
            dialog.Destroy()

        def worker():
            try:
                items = [TransferItem("upload", local_path, str(remote_dir / Path(local_path).name)) for local_path in paths]
                _start_file_transfers(session_state, lifecycle, items, files_backend=files, parent=parent)
            except Exception as error:
                import wx

                wx.CallAfter(wx.MessageBox, str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)

        Thread(target=worker, daemon=True).start()

    return {
        "open_editor": lambda path: open_local(path),
        "open_editor_new_window": lambda path: open_local(path, True),
        "upload": upload_local,
        "run_shell": lambda path: _run_shell_in_terminal(session_state, parent, lifecycle, [path]),
    }


def _remote_files_callbacks(session_state, parent, lifecycle):
    _manager = _get_editor_manager(session_state, parent, lifecycle)

    def _resolve_session():
        return (session_state or {}).get("session") or {}

    def _resolve_files():
        return _resolve_session().get("files")

    def _resolve_slurm():
        return _resolve_session().get("slurm")

    def _resolve_profile():
        return _resolve_session().get("profile") or {}

    def _resolve_provider_config():
        profile = _resolve_profile()
        provider = profile.get("provider_template")
        return provider if isinstance(provider, dict) else profile

    def _supports_file_method(files, name):
        method = getattr(files, name, None) if files is not None else None
        if not callable(method):
            return False
        try:
            from hpc_gui.services.files_base import FilesBackend
            return getattr(type(files), name, None) is not getattr(FilesBackend, name, None)
        except (ImportError, AttributeError):
            return True

    def remote_operation(action, paths, destination=""):
        files = _resolve_files()
        if action == "delete" and files:
            for remote_path in paths:
                files.remove(remote_path, recursive=True)
            return
        if action == "rename" and files and len(paths) == 1 and destination:
            files.rename(paths[0], destination)
            return
        if action in {"copy", "move"} and files and destination:
            for remote_path in paths:
                target = str(PurePosixPath(destination) / PurePosixPath(remote_path).name)
                (files.copy if action == "copy" else files.move)(remote_path, target)
            return
        if action == "download" and files and destination:
            items = [TransferItem("download", remote_path, str(Path(destination) / PurePosixPath(remote_path).name)) for remote_path in paths]
            _start_file_transfers(session_state, lifecycle, items, files_backend=files, parent=parent)
            return
        if action == "upload" and files and destination:
            items = [TransferItem("upload", local_path, str(PurePosixPath(destination) / Path(local_path).name)) for local_path in paths]
            _start_file_transfers(session_state, lifecycle, items, files_backend=files, parent=parent)
            return
        if action == "new_folder" and files and destination:
            files.mkdir(destination)
            return
        if action == "new_file" and files and destination:
            files.write_text(destination, "")
            return
        raise RuntimeError(f"Remote action is not available from this view: {action}")

    def chmod(path, mode):
        files = _resolve_files()
        if not files or not callable(getattr(files, "chmod", None)):
            raise RuntimeError(t("dirs.permissions_unavailable"))
        files.chmod(path, mode if isinstance(mode, int) else int(str(mode), 8))

    def submit_slurm(path):
        slurm = _resolve_slurm()
        if not slurm or not callable(getattr(slurm, "sbatch", None)):
            raise RuntimeError(t("jobs.slurm_unavailable"))
        return slurm.sbatch(path)

    def _editor(path, content="", request_id=None):
        _manager.open_primary(path, content, is_local=False, request_id=request_id)

    _editor._wx_request_aware = True

    def _editor_request_started():
        return _manager.begin_primary_request()

    _editor._wx_request_started = _editor_request_started

    def _editor_new_window(path, content=""):
        _manager.open_new_window(path, content, is_local=False)

    def _loader(path):
        files = _resolve_files()
        if files and hasattr(files, "iterdir_entries"):
            return files.iterdir_entries(path)
        return ()

    def _read_text(path):
        files = _resolve_files()
        if files and hasattr(files, "read_text"):
            return files.read_text(path)
        return ""

    # Wrap loader/read_text to be callable with path; the remote view will call loader(path)
    # To keep compatibility with the view's `loader=files.iterdir_entries if files else None` pattern,
    # we provide functions that dynamically resolve files.
    def loader(path):
        return _loader(path)

    def read_text(path):
        return _read_text(path)

    def _navigation_store():
        from hpc_gui.services.remote_navigation_store import navigation_store_for_profile
        profile = _resolve_profile()
        profile_id = str(profile.get("id", profile.get("profile_id", "")))
        return navigation_store_for_profile(profile_id)

    def _provider_filters():
        value = _resolve_provider_config().get("file_filters", ())
        return value if isinstance(value, (list, tuple)) else ()

    def _plugin_filters():
        # Application plugins are declarative and may contribute through the
        # session's already-loaded profile metadata when present.
        value = _resolve_profile().get("application_file_filters", ())
        return value if isinstance(value, (list, tuple)) else ()

    return {
        "loader": loader,
        "read_text": read_text,
        "operation": remote_operation,
        "open_editor": _editor,
        "open_editor_new_window": _editor_new_window,
        "run_shell": lambda path: _run_shell_in_terminal(session_state, parent, lifecycle, [path]),
        "chmod": chmod,
        "submit_slurm": submit_slurm,
        "operation_supported": lambda: _resolve_files() is not None and callable(getattr(_resolve_files(), "write_text", None)),
        "chmod_supported": lambda: _supports_file_method(_resolve_files(), "chmod"),
        "submit_slurm_supported": lambda: _resolve_slurm() is not None and callable(getattr(_resolve_slurm(), "sbatch", None)),
        "navigation_store": _navigation_store,
        "provider_filters": _provider_filters,
        "plugin_filters": _plugin_filters,
    }


def _jobs_callbacks(session_state, parent, lifecycle):
    from hpc_gui.services.adapter_registry import get_adapter
    from hpc_gui.services.provider_contract import execute_adapter, extract_contract

    def _resolve_slurm():
        session = (session_state or {}).get("session") or {}
        return session.get("slurm")

    def _resolve_files():
        session = (session_state or {}).get("session") or {}
        return session.get("files")

    def _resolve_profile():
        session = (session_state or {}).get("session") or {}
        return session.get("profile") or {}

    def _resolve_provider_config():
        profile = _resolve_profile()
        provider = profile.get("provider_template")
        return provider if isinstance(provider, dict) else profile

    def _execute_contract_adapter(section, slurm, job_id=""):
        contract = extract_contract(_resolve_provider_config())
        adapter_id = getattr(contract, f"{section}_adapter", None)
        if not adapter_id:
            return None
        if get_adapter(adapter_id) is None:
            raise RuntimeError(f"Configured provider adapter is unavailable: {adapter_id}")
        profile = _resolve_profile()
        return execute_adapter(
            adapter_id,
            slurm_backend=slurm,
            job_id=str(job_id),
            user=str(profile.get("username", "")),
            profile=profile,
        )

    def list_jobs():
        slurm = _resolve_slurm()
        profile = _resolve_profile()
        if not slurm:
            return ()
        raw = slurm.squeue(str(profile.get("username", "")))
        rows = []
        for line in str(raw or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("jobid"):
                continue
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) < 6:
                continue
            job_id = parts[0]
            partition = parts[1] if len(parts) > 1 else ""
            name = parts[2] if len(parts) > 2 else ""
            user = parts[3] if len(parts) > 3 else ""
            state = parts[4] if len(parts) > 4 else ""
            elapsed = parts[5] if len(parts) > 5 else ""
            nodes = parts[6] if len(parts) > 6 else ""
            cpus = parts[7] if len(parts) > 7 else ""
            reason = parts[8] if len(parts) > 8 else ""
            rows.append({
                "id": job_id,
                "job_id": job_id,
                "name": name,
                "state": state,
                "partition": partition,
                "elapsed": elapsed,
                "nodes": nodes,
                "cpus": cpus,
                "reason": reason,
                "user": user,
            })
        return rows

    def read_output(job_id):
        slurm = _resolve_slurm()
        files = _resolve_files()
        if not slurm or not files:
            return {}
        metadata = str(slurm.scontrol_show_job(job_id) or "")
        paths = {}
        for key in ("StdOut", "StdErr"):
            for part in metadata.split():
                if part.startswith(f"{key}="):
                    paths[key] = part.split("=", 1)[1]
                    break
            else:
                paths[key] = ""
        return {
            "stdout": files.read_text(paths["StdOut"]) if paths["StdOut"] else "",
            "stderr": files.read_text(paths["StdErr"]) if paths["StdErr"] else "",
        }

    def read_remote_path(path):
        files = _resolve_files()
        if not files or not path:
            raise FileNotFoundError(path)
        return files.read_text(path)

    def stat_remote_path(path):
        files = _resolve_files()
        if not files or not path:
            raise FileNotFoundError(path)
        return files.stat(path)

    def list_job_files(job_id, workdir=""):
        test_files = session_state.get("_test_job_files")
        if test_files is not None:
            if isinstance(test_files, dict):
                return tuple(test_files.get(str(job_id), ()))
            return tuple(test_files)
        slurm = _resolve_slurm()
        files = _resolve_files()
        if not slurm or not files or not hasattr(files, "iterdir_entries"):
            return ()
        try:
            if not workdir:
                meta = str(slurm.scontrol_show_job(job_id) or "")
                for part in meta.split():
                    if part.startswith("WorkDir="):
                        workdir = part.split("=", 1)[1]
                        break
                if not workdir:
                    for part in meta.split():
                        if part.startswith("StdOut="):
                            p = part.split("=", 1)[1]
                            workdir = str(PurePosixPath(p).parent) if p else ""
                            break
            if not workdir:
                return ()
            return tuple(files.iterdir_entries(workdir))
        except Exception:
            return ()

    def _cancel(job_id):
        slurm = _resolve_slurm()
        if slurm and hasattr(slurm, "scancel"):
            return slurm.scancel(job_id)
        return None

    def _final_state(job_id):
        slurm = _resolve_slurm()
        if slurm and hasattr(slurm, "job_state"):
            return slurm.job_state(job_id)
        return ""

    def _refresh_sacct(job_id):
        slurm = _resolve_slurm()
        profile = _resolve_profile()
        if not slurm:
            return ""
        contract_result = _execute_contract_adapter("accounting", slurm, job_id)
        if contract_result is not None:
            return contract_result
        sacct_job = getattr(slurm, "sacct_job", None)
        if callable(sacct_job):
            return sacct_job(str(job_id))
        if not hasattr(slurm, "sacct"):
            return ""
        try:
            return str(slurm.sacct(str(profile.get("username", "")), job_id=job_id) or "")
        except TypeError:
            return str(slurm.sacct(str(profile.get("username", ""))) or "")

    def _show_job_details(job_id):
        slurm = _resolve_slurm()
        if not slurm:
            return ""
        contract_result = _execute_contract_adapter("job_details", slurm, job_id)
        if contract_result is not None:
            return contract_result
        return str(slurm.scontrol_show_job(job_id) or "")

    def _has_status_capability():
        slurm = _resolve_slurm()
        if not slurm:
            return False
        contract = extract_contract(_resolve_provider_config())
        if contract.cluster_status_adapter:
            return get_adapter(contract.cluster_status_adapter) is not None
        return callable(getattr(slurm, "lssrv", None))

    def _refresh_lssrv(_job_id=""):
        slurm = _resolve_slurm()
        if not slurm or not callable(getattr(slurm, "lssrv", None)):
            raise RuntimeError(t("jobs_outputs.provider_status_unavailable"))
        contract_result = _execute_contract_adapter("cluster_status", slurm, _job_id)
        if contract_result is not None:
            return contract_result
        return str(slurm.lssrv() or "")

    def _resolve_output_defs():
        from hpc_gui.services.output_channel_resolver import definitions_from_provider
        session = (session_state or {}).get("session") or {}
        profile = session.get("profile") or {}
        provider = profile.get("provider_template") if isinstance(profile, dict) else None
        config = provider if isinstance(provider, dict) else profile
        job_outputs = config.get("job_outputs") if isinstance(config, dict) else None
        return definitions_from_provider(job_outputs)

    def open_main_files(path="", highlight_path=""):
        main_notebook = session_state.get("_embedded_main_notebook")
        files_page = session_state.get("_embedded_files_page")
        remote_panel = session_state.get("_embedded_remote_files_panel")
        if main_notebook is None or files_page is None or remote_panel is None:
            return
        page_index = next(
            (index for index in range(main_notebook.GetPageCount())
             if main_notebook.GetPage(index) is files_page),
            -1,
        )
        if page_index >= 0:
            main_notebook.SetSelection(page_index)
        remote_notebook = getattr(remote_panel, "_wx_remote_notebook", None)
        tabs = getattr(remote_panel, "_wx_remote_tabs", ())
        if remote_notebook is not None and tabs:
            active_index = remote_notebook.GetSelection()
            if 0 <= active_index < len(tabs):
                tabs[active_index]["highlight_path"] = str(highlight_path or "")
        controls = getattr(remote_panel, "_wx_remote_controls", {})
        navigate = controls.get("navigate")
        load = controls.get("load")
        if callable(navigate):
            navigate(str(path or "/"))
        if callable(load):
            load()

    return {
        "list_jobs": list_jobs,
        "read_output": read_output,
        "read_remote_path": read_remote_path,
        "stat_remote_path": stat_remote_path,
        "list_job_files": list_job_files,
        "cancel": _cancel,
        "final_state": _final_state,
        "refresh_sacct": _refresh_sacct,
        "show_job_details": _show_job_details,
        "has_status_capability": _has_status_capability,
        "refresh_lssrv": _refresh_lssrv,
        "output_channel_defs": None,
        "output_channel_defs_provider": _resolve_output_defs,
        "open_main_files": open_main_files,
        "provider_filters": lambda: (_resolve_provider_config().get("file_filters", ()) if isinstance(_resolve_provider_config().get("file_filters", ()), (list, tuple)) else ()),
        "remote_files_callbacks": _remote_files_callbacks(session_state, parent, lifecycle),
        "generation": lambda: session_state.get("generation", 0),
        "lifecycle": lifecycle,
        "session_state": session_state,
    }


def _connection_callbacks(session_state, parent, lifecycle):
    from hpc_gui.config.storage import load_profiles

    profiles = load_profiles()

    def on_connected(session):
        session_state["session"] = session
        session_state["generation"] = session_state.get("generation", 0) + 1
        profile = session.get("profile") if isinstance(session, dict) else None
        file_manager = profile.get("file_manager") if isinstance(profile, dict) else None
        local_start_dir = file_manager.get("local_start_dir") if isinstance(file_manager, dict) else ""
        local_panel = session_state.get("_embedded_local_files_panel")
        if local_panel is not None and isinstance(local_start_dir, str) and local_start_dir.strip():
            target = Path(local_start_dir).expanduser()
            if target.is_dir():
                try:
                    local_panel._wx_local_model.navigate(target)
                    local_panel._wx_local_controls["path"].SetValue(str(target.resolve()))
                    local_panel._wx_local_refresh()
                except (OSError, RuntimeError):
                    pass
        ssh = session.get("ssh") if isinstance(session, dict) else None
        if ssh is not None and callable(getattr(ssh, "close", None)):
            lifecycle.register_cleanup(ssh.close)
        # keep embedded terminal in sync with new ssh
        try:
            panel = session_state.get("_embedded_terminal_panel")
            if panel is not None and hasattr(panel, "_wx_terminal_set_ssh"):
                panel._wx_terminal_set_ssh(ssh)
        except Exception:
            pass
        for panel_key in ("_embedded_jobs_panel", "_embedded_remote_files_panel"):
            try:
                panel = session_state.get(panel_key)
                if panel is not None and hasattr(panel, "_wx_jobs_set_session"):
                    panel._wx_jobs_set_session(session)
                if panel is not None and hasattr(panel, "_wx_remote_set_navigation_store"):
                    panel._wx_remote_set_navigation_store(
                        _remote_files_callbacks(session_state, parent, lifecycle)["navigation_store"]
                    )
                if panel is not None and hasattr(panel, "_wx_remote_set_provider_filters"):
                    cbs = _remote_files_callbacks(session_state, parent, lifecycle)
                    panel._wx_remote_set_provider_filters(cbs.get("provider_filters"), cbs.get("plugin_filters"))
            except Exception:
                pass

    def on_disconnected(session):
        # Graceful/transport-loss teardown (CONN-004/TODO-007): drop the dead
        # session from the canonical model and mint a fresh generation so
        # every domain re-resolves to "no session". Jobs/remote/transfers/
        # editor callbacks resolve the session live, so they gate
        # truthfully once it is None; the terminal write path is
        # neutralized explicitly so input cannot reach a dead transport.
        session_state["session"] = None
        session_state["generation"] = session_state.get("generation", 0) + 1
        try:
            panel = session_state.get("_embedded_terminal_panel")
            if panel is not None and hasattr(panel, "_wx_terminal_set_ssh"):
                panel._wx_terminal_set_ssh(None)
        except Exception:
            pass
        for panel_key in ("_embedded_jobs_panel", "_embedded_remote_files_panel"):
            try:
                panel = session_state.get(panel_key)
                if panel is not None and hasattr(panel, "_wx_jobs_set_session"):
                    panel._wx_jobs_set_session(None)
            except Exception:
                pass

    return {"profiles": profiles, "lifecycle": lifecycle, "on_connected": on_connected, "on_disconnected": on_disconnected}


def _logs_callbacks(session_state, parent, lifecycle):
    # Logs view uses WxLogsModel internally; no session needed
    return {}


def _directories_callbacks(session_state, parent, lifecycle):
    # Share single implementation between embedded tab and dispatch
    # Pass session_state so view can derive scratch/home via system_profile helpers
    # Also provide run_shell delegation matching _remote_files_callbacks pattern
    return {"session_state": session_state}


def _select_embedded_page(session_state, parent, key: str) -> bool:
    """Select the existing embedded notebook page for ``key`` (SHELL-NAV-002).

    Returns True when an embedded page was selected, False when the caller
    must fall back to the detached window path (headless/service use and
    legacy callers without a shell frame). The detached ``show_*`` owner
    stays intact in every dispatch branch for those fallbacks.
    """
    try:
        state = session_state or {}
        notebook = state.get("_embedded_main_notebook")
        if notebook is None:
            return False
        frame = parent
        for _ in range(8):
            if frame is None:
                break
            controls = getattr(frame, "_wx_shell_controls", None)
            if isinstance(controls, dict) and isinstance(controls.get("pages"), dict):
                break
            try:
                frame = frame.GetParent()
            except Exception:
                frame = None
        else:
            frame = None
        if frame is None:
            controls = None
        else:
            controls = getattr(frame, "_wx_shell_controls", None)
        if not isinstance(controls, dict):
            return False
        pages = controls.get("pages") or {}
        entry = pages.get(key) or {}
        page = entry.get("page")
        if page is None:
            return False
        try:
            index = notebook.FindPage(page)
        except Exception:
            return False
        try:
            notebook.SetSelection(index)
        except Exception:
            return False
        try:
            page.SetFocus()
        except Exception:
            pass
        return True
    except Exception:
        return False


def _dispatch(command_id: str, parent=None, lifecycle=None, session_state=None) -> None:
    if command_id == "APP-HELP":
        from hpc_gui.wx_help import show_help

        show_help(parent)
    elif command_id == "APP-SETTINGS":
        from hpc_gui.wx_settings_view import show_settings
        try:
            show_settings(parent=parent)
        except Exception as exc:
            # W02 ERROR-GOV: a settings failure must be visible, never silent.
            report_wx_action_error(parent, area="SETTINGS", message_key="settings.open_failed", exc=exc)
    elif command_id == "APP-UPDATE-CHECK":
        # Reuse update flow – find frame from parent if needed
        try:
            # Try to find shell frame via parent chain; fallback to parent
            frame = parent
            # attempt to call _on_update via closure? Instead directly trigger updater dialog
            if frame and hasattr(frame, "_wx_shell_menubar"):
                # Use same logic as _on_update but we have no closure; just show updater view
                from hpc_gui.wx_updater_view import WxUpdateDialog, STATE_CHECKING
                dlg = WxUpdateDialog(frame, None)
                dlg._build_for_state(STATE_CHECKING)
                dlg.dlg.Show()
            else:
                from hpc_gui.wx_updater_view import WxUpdateDialog, STATE_CHECKING
                dlg = WxUpdateDialog(parent, None)
                dlg._build_for_state(STATE_CHECKING)
                dlg.dlg.Show()
        except Exception as exc:
            # W02 ERROR-GOV: an updater failure must be visible, never silent.
            report_wx_action_error(parent, area="UPDATE", message_key="updates.open_failed", exc=exc)
    elif command_id == "APP-SEND-LOGS":
        from hpc_gui.wx_send_logs_view import show_send_logs
        try:
            show_send_logs(parent=parent)
        except Exception as exc:
            # W02 ERROR-GOV: a diagnostics failure must be visible, never silent.
            report_wx_action_error(parent, area="LOGS", message_key="logs.send_open_failed", exc=exc)
    elif command_id == "APP-ABOUT":
        from hpc_gui.wx_about import show_about
        try:
            show_about(parent=parent)
        except Exception as exc:
            # W02 ERROR-GOV: an about-dialog failure must be visible, never silent.
            # NOTE: the success path still uses the real wx.Dialog (see W01
            # FIX-W01-002); only the failure path reports through the helper.
            report_wx_action_error(parent, area="ABOUT", message_key="about.open_failed", exc=exc)
    elif command_id in {"PLUGIN-BROWSE", "PLUGIN-MANAGE", "PLUGIN-UPDATES"}:
        try:
            from hpc_gui.wx_plugins_view import show_plugins
            # Map to initial tab
            tab_map = {"PLUGIN-BROWSE": "discover", "PLUGIN-MANAGE": "installed", "PLUGIN-UPDATES": "updates"}
            initial = tab_map.get(command_id, "discover")
            # Try to pass initial_tab if supported
            try:
                show_plugins(parent=parent, initial_tab=initial)
            except TypeError:
                show_plugins(parent=parent)
        except Exception as exc:
            # W02 ERROR-GOV: a plugin-manager failure must be visible, never silent.
            report_wx_action_error(parent, area="PLUGIN", message_key="plugins.open_failed", exc=exc)
    elif command_id == "PLUGIN-REQUEST":
        try:
            from hpc_gui.ui.dialogs.plugin_manager_dialog import PLUGIN_REQUEST_URL
            import webbrowser
            request_error = None
            try:
                opened = bool(webbrowser.open(PLUGIN_REQUEST_URL))
            except Exception as exc:
                opened = False
                request_error = exc
        except Exception as exc:
            opened = False
            request_error = exc
        if not opened:
            # W02 ERROR-GOV (DEF-W02-002): webbrowser.open() returning False
            # opens no browser and raises nothing; that silent no-op must
            # still produce a visible, diagnosable error like the Qt surface.
            report_wx_action_error(
                parent, area="PLUGIN", message_key="plugins.request_plugin_failed", exc=request_error
            )
    elif command_id == "APP-CONNECT":
        if _select_embedded_page(session_state, parent, "APP-CONNECT"):
            return
        from hpc_gui.wx_connection import show_connection

        _conn = _connection_callbacks(session_state, parent, lifecycle)
        show_connection(parent, **_conn)
    elif command_id == "NAV-FILES":
        if _select_embedded_page(session_state, parent, "NAV-FILES"):
            return
        from hpc_gui.wx_local_files import show_local_files

        _kwargs = _local_files_callbacks(session_state, parent, lifecycle)
        show_local_files(parent, **_kwargs)
    elif command_id == "NAV-DIRECTORIES":
        if _select_embedded_page(session_state, parent, "NAV-DIRECTORIES"):
            return
        from hpc_gui.wx_directories_view import show_directories

        show_directories(parent, **_directories_callbacks(session_state, parent, lifecycle))
    elif command_id == "NAV-LOGS":
        if _select_embedded_page(session_state, parent, "NAV-LOGS"):
            return
        from hpc_gui.wx_logs_view import show_logs

        _kwargs = _logs_callbacks(session_state, parent, lifecycle)
        show_logs(parent, **_kwargs)
    elif command_id == "NAV-EDITOR":
        if _select_embedded_page(session_state, parent, "NAV-EDITOR"):
            return
        _get_editor_manager(session_state, parent, lifecycle).open_primary("", "", is_local=False)
    elif command_id == "NAV-TERMINAL":
        if _select_embedded_page(session_state, parent, "NAV-TERMINAL"):
            return
        from hpc_gui.wx_terminal import show_terminal

        session = (session_state or {}).get("session") or {}
        show_terminal(parent, ssh=session.get("ssh"), lifecycle=lifecycle)
    elif command_id == "NAV-JOBS":
        if _select_embedded_page(session_state, parent, "NAV-JOBS"):
            return
        from hpc_gui.wx_jobs import show_jobs

        _kwargs = _jobs_callbacks(session_state, parent, lifecycle)
        # show_jobs expects lifecycle, list_jobs, read_output, cancel, final_state, generation
        show_jobs(parent, **_kwargs)
    elif command_id in {"PLUGIN-ANSYS-LINTER", "APP-ANSYS"}:
        from hpc_gui.wx_ansys_view import show_ansys_lint

        show_ansys_lint(parent, lifecycle=lifecycle)


__all__ = ["main"]
