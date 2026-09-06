"""Optional wxPython migration shell; Qt remains the default runtime."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from pathlib import PurePosixPath
from threading import Event, Thread

from hpc_gui import __version__
from hpc_gui.core.i18n import current_language, load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change
from hpc_gui.services.command_registry import COMMAND_REGISTRY
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


def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_state=None):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed; use the default Qt runtime") from exc
    if app is None:
        app = wx.App(False)
    lifecycle = lifecycle or WxLifecycleController()
    session_state = session_state or {"session": None, "generation": 0}
    frame = wx.Frame(None, title=f"HPC Client GUI {__version__}", size=(1440, 900))
    # Spec §3: recommended 1440×900 default, 1280×760 minimum; usable at ~1100×700 without clipping
    frame.SetMinSize(wx.Size(1280, 760))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    menu = wx.Menu()
    command_items = []
    for command in COMMAND_REGISTRY.by_context("shell"):
        item = menu.Append(wx.ID_ANY, command.label())
        command_items.append((command, item))
        frame.Bind(wx.EVT_MENU, lambda _event, command_id=command.id: _dispatch(command_id, frame, lifecycle, session_state), item)
    frame.SetMenuBar(wx.MenuBar())
    frame.GetMenuBar().Append(menu, t("help.help_title"))
    language_menu = wx.Menu()
    language_items = {}
    for language, key in (("en", "english"), ("tr", "turkish")):
        item = language_menu.AppendRadioItem(wx.ID_ANY, t(f"language.{key}"), t(f"language.{key}"))
        item.SetBitmap(_flag_bitmap(wx, language))
        language_items[language] = item
        frame.Bind(wx.EVT_MENU, lambda _event, language=language: set_language(language), item)
    frame.GetMenuBar().Append(language_menu, t("help.language"))
    # --- Level 1 chrome row §2: Update | Plugins | Send Logs | Settings | Help | Language ▼ | vX.X (version far right) ---
    chrome_sizer = wx.BoxSizer(wx.HORIZONTAL)
    # Spec §6: primary 30-32px height, min width 88px; secondary native bordered
    def _chrome_button(label):
        btn = wx.Button(panel, label=label)
        try:
            btn.SetMinSize(wx.Size(88, 30))
        except Exception:
            pass
        return btn
    version_label = wx.StaticText(panel, label=f"v{__version__}")
    # Low emphasis per §104: no button border/hover affordance
    try:
        version_label.SetForegroundColour(wx.Colour(85, 85, 85))
        fnt = version_label.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_NORMAL)
        version_label.SetFont(fnt)
    except Exception:
        pass
    update_btn = _chrome_button(t("updates.action"))
    plugins_btn = _chrome_button(t("plugins.action"))
    send_logs_btn = _chrome_button(t("crash.send_logs_btn"))
    settings_btn = _chrome_button(t("settings.action"))
    help_btn = _chrome_button(t("help.help_title"))
    cur_lang = current_language()
    language_button = wx.Button(panel, label=t("language.english") if cur_lang == "en" else t("language.turkish"))
    try:
        language_button.SetMinSize(wx.Size(110, 30))
        language_button.SetBitmap(_flag_bitmap(wx, cur_lang))
    except Exception:
        pass
    # Spec §2 order left→right: Update, Plugins, Send Logs, Settings, Help, Language, Version (version at far right)
    chrome_sizer.Add(update_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    chrome_sizer.Add(plugins_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    chrome_sizer.Add(send_logs_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    chrome_sizer.Add(settings_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    chrome_sizer.Add(help_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    chrome_sizer.Add(language_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    chrome_sizer.AddStretchSpacer(1)
    chrome_sizer.Add(version_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
    # Spec §4: default panel padding 12px
    root.Add(chrome_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    notebook = wx.Notebook(panel)
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

    # Jobs & Outputs
    _jobs = _jobs_callbacks(session_state, frame, lifecycle)
    jobs_panel = build_jobs_panel(notebook, **_jobs)
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
    remote_panel = build_remote_files_panel(top_splitter, **_remote)
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
        run = getattr(remote_panel, "_wx_remote_run_action", None)
        if callable(run):
            run("download")

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
    notebook.AddPage(editor_panel, t("tabs.editor"), False)
    page_controls["NAV-EDITOR"] = {"page": editor_panel}

    # Terminal — unified reusable panel (same as detached)
    from hpc_gui.wx_terminal import build_terminal_panel as _build_terminal_panel
    _term_session = session_state.get("session") or {}
    _term_ssh = _term_session.get("ssh")
    terminal_page = _build_terminal_panel(notebook, ssh=_term_ssh, lifecycle=lifecycle)
    # expose for session updates; on_connected will call _wx_terminal_set_ssh
    session_state["_embedded_terminal_panel"] = terminal_page
    notebook.AddPage(terminal_page, t("help.section_terminal"), False)
    # keep backward-compatible controls map plus direct panel controls
    _term_controls = getattr(terminal_page, "_wx_terminal_controls", {})
    page_controls["NAV-TERMINAL"] = {"page": terminal_page, **_term_controls, "output": _term_controls.get("output"), "panel": terminal_page}

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
        frame.GetMenuBar().SetMenuLabel(0, t("help.help_title"))
        frame.GetMenuBar().SetMenuLabel(1, t("help.language"))
        for index, title_key in enumerate(("tabs.login", "tabs.jobs_outputs", "tabs.directories", "tabs.ftp", "tabs.editor", "help.section_terminal", "tabs.logs")):
            notebook.SetPageText(index, t(title_key))
        for command, item in command_items:
            menu.SetLabel(item.GetId(), command.label())
        for language, item in language_items.items():
            language_menu.SetLabel(item.GetId(), t("help.english" if language == "en" else "help.turkish"))
            item.Check(current_language() == language)
        # chrome row
        version_label.SetLabel(f"v{__version__}")
        update_btn.SetLabel(t("updates.action"))
        plugins_btn.SetLabel(t("plugins.action"))
        send_logs_btn.SetLabel(t("crash.send_logs_btn"))
        settings_btn.SetLabel(t("settings.action"))
        help_btn.SetLabel(t("help.help_title"))
        cur = current_language()
        language_button.SetLabel(t("language.english") if cur == "en" else t("language.turkish"))
        try:
            language_button.SetBitmap(_flag_bitmap(wx, cur))
        except Exception:
            pass
        language_button.SetToolTip(t("help.language"))
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
        # Spec §83-90: structured update dialogs with real byte progress
        try:
            from hpc_gui.wx_updater_view import (
                show_update_checking,
                show_up_to_date,
                show_update_available,
                show_download_progress,
                show_update_ready,
                show_installing_splash,
                show_update_error,
            )
        except Exception:
            # Fallback to simple message if view not available
            show_update_checking = None  # type: ignore

        # Show checking dialog immediately (indeterminate) per §84
        checking_dlg = None
        checking_timer = None
        checking_cancelled = {"v": False}
        if show_update_checking is not None:
            try:
                checking_dlg, checking_cancelled, checking_timer = show_update_checking(parent=f, lifecycle=lifecycle)
                checking_dlg.Show()
                _track_new_windows(before)
            except Exception:
                checking_dlg = None

        def worker():
            try:
                from hpc_gui.services.app_updater import (
                    get_latest_release,
                    is_newer_version,
                    download_and_verify_release,
                    launch_update_installer,
                )
                from hpc_gui.services.app_updater import AUTOMATIC_INSTALL_STRATEGIES
                from hpc_gui.core.paths import is_frozen_exe
                from hpc_gui.core.platform import current_os
                from hpc_gui import __version__ as cur_ver

                release = get_latest_release()
                if checking_cancelled.get("v"):
                    def on_cancelled():
                        try:
                            if checking_dlg is not None:
                                checking_dlg.EndModal(wx.ID_CANCEL)
                                checking_dlg.Destroy()
                        except Exception:
                            pass
                    wx.CallAfter(on_cancelled)
                    return

                def on_done():
                    ff = _shell_frame()
                    if not ff:
                        return
                    try:
                        if not wx.Window.FindWindowById(ff.GetId()):
                            return
                    except Exception:
                        return
                    # Close checking dialog
                    try:
                        if checking_dlg is not None:
                            checking_timer.Stop()  # type: ignore
                            checking_dlg.EndModal(wx.ID_OK)
                            checking_dlg.Destroy()
                    except Exception:
                        pass
                    try:
                        if not is_newer_version(release.version, cur_ver):
                            show_up_to_date(ff, cur_ver)
                            _track_new_windows(before)
                            return
                        # Check install strategy per app.py logic
                        try:
                            from hpc_gui.services import app_updater as _au
                            macos_auto_supported = not (
                                release.install_strategy == "macos-bundle"
                                and release.security_status != _au.SECURITY_SIGNED
                            )
                        except Exception:
                            macos_auto_supported = True
                        if release.install_strategy not in AUTOMATIC_INSTALL_STRATEGIES or not macos_auto_supported:
                            # Manual install per original flow
                            import webbrowser
                            msg = t("updates.manual_install").format(version=release.version) if t("updates.manual_install") != "[updates.manual_install]" else f"Update {release.version} requires manual install."
                            if current_os() == "macos":
                                try:
                                    sec_key = {
                                        _au.SECURITY_UNSIGNED: "updates.security_unsigned_mac",
                                        _au.SECURITY_SIGNED: "updates.security_signed_mac",
                                        _au.SECURITY_UNKNOWN: "updates.security_unknown_mac",
                                    }.get(release.security_status, "updates.security_unknown_mac")
                                    msg += "\n\n" + t(sec_key)
                                except Exception:
                                    pass
                            wx.MessageBox(msg, t("updates.title"), wx.OK | wx.ICON_INFORMATION, ff)
                            try:
                                webbrowser.open(release.zip_url or release.html_url)
                            except Exception:
                                pass
                            _track_new_windows(before)
                            return
                        # Spec §86: Update available dialog
                        if not show_update_available(ff, cur_ver, release.version):
                            _track_new_windows(before)
                            return
                        # Spec §87: Download progress with real bytes
                        dl_dlg = show_download_progress(ff, release.version, lifecycle=lifecycle)
                        dl_dlg.Show()
                        _track_new_windows(before)
                        # Track cancel
                        def dl_worker():
                            try:
                                def progress_cb(value, status, downloaded, total):
                                    def apply():
                                        if not dl_dlg.IsShown():
                                            return
                                        dl_dlg._wx_updater_update(downloaded, total, status)
                                    try:
                                        wx.CallAfter(apply)
                                    except Exception:
                                        pass
                                # Provide cancelled callback
                                def cancelled():
                                    return bool(dl_dlg._wx_updater_state.get("cancelled") or checking_cancelled.get("v") or (lifecycle.cancel_token.is_set() if lifecycle else False))
                                zip_path = download_and_verify_release(release, progress_cb=progress_cb, cancelled=cancelled)
                                def on_dl_done():
                                    try:
                                        dl_dlg.EndModal(wx.ID_OK)
                                        dl_dlg.Destroy()
                                    except Exception:
                                        pass
                                    # Spec §88 verifying → ready
                                    if show_update_ready(ff, release.version):
                                        # Spec §89 installing splash 620×360
                                        install_dlg = show_installing_splash(ff, release.version)
                                        install_dlg.Show()
                                        _track_new_windows(before)
                                        try:
                                            launch_update_installer(zip_path, release.version, release.install_strategy)
                                        except Exception as exc_install:
                                            try:
                                                install_dlg.EndModal(wx.ID_CANCEL)
                                                install_dlg.Destroy()
                                            except Exception:
                                                pass
                                            if show_update_error(ff, str(exc_install)):
                                                # Retry delegate to outer handler
                                                _on_update(None)  # type: ignore
                                            return
                                        # Success → quit app per original flow
                                        try:
                                            install_dlg.EndModal(wx.ID_OK)
                                            install_dlg.Destroy()
                                        except Exception:
                                            pass
                                        try:
                                            wx.GetApp().ExitMainLoop()
                                        except Exception:
                                            try:
                                                wx.Exit()
                                            except Exception:
                                                pass
                                    else:
                                        _track_new_windows(before)
                                wx.CallAfter(on_dl_done)
                            except Exception as exc_dl:
                                def on_dl_err():
                                    try:
                                        dl_dlg.EndModal(wx.ID_CANCEL)
                                        dl_dlg.Destroy()
                                    except Exception:
                                        pass
                                    # Spec §90 error with retry
                                    try:
                                        if show_update_error(ff, str(exc_dl)):
                                            _on_update(None)  # type: ignore
                                    except Exception:
                                        try:
                                            wx.MessageBox(str(exc_dl), t("updates.error_title"), wx.OK | wx.ICON_ERROR, ff)
                                        except Exception:
                                            pass
                                wx.CallAfter(on_dl_err)
                        Thread(target=dl_worker, daemon=True).start()
                    except Exception as exc:
                        try:
                            if show_update_error(ff, str(exc)):
                                _on_update(None)  # type: ignore
                            else:
                                wx.MessageBox(str(exc), t("updates.error_title"), wx.OK | wx.ICON_ERROR, ff)
                        except Exception:
                            pass

                wx.CallAfter(on_done)
            except Exception as exc:
                def on_err(exc=exc):
                    ff = _shell_frame()
                    if not ff:
                        return
                    try:
                        if checking_dlg is not None:
                            checking_timer.Stop()  # type: ignore
                            checking_dlg.EndModal(wx.ID_CANCEL)
                            checking_dlg.Destroy()
                    except Exception:
                        pass
                    try:
                        if show_update_error is not None:
                            if show_update_error(ff, str(exc)):
                                _on_update(None)  # type: ignore
                        else:
                            wx.MessageBox(t("updates.error_message").format(error=str(exc)), t("updates.error_title"), wx.OK | wx.ICON_ERROR, ff)
                    except Exception:
                        pass
                try:
                    wx.CallAfter(on_err)
                except Exception:
                    pass

        Thread(target=worker, daemon=True).start()

    def _on_plugins(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        try:
            from hpc_gui.wx_plugins_view import show_plugins
            show_plugins(parent=f)
        except Exception:
            pass
        _track_new_windows(before)

    def _on_send_logs(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        try:
            from hpc_gui.wx_send_logs_view import show_send_logs
            show_send_logs(parent=f)
        except Exception:
            pass
        _track_new_windows(before)

    def _on_settings(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        try:
            from hpc_gui.wx_settings_view import show_settings
            show_settings(parent=f)
        except Exception:
            pass
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

    help_btn.Bind(wx.EVT_BUTTON, _on_help)
    update_btn.Bind(wx.EVT_BUTTON, _on_update)
    plugins_btn.Bind(wx.EVT_BUTTON, _on_plugins)
    send_logs_btn.Bind(wx.EVT_BUTTON, _on_send_logs)
    settings_btn.Bind(wx.EVT_BUTTON, _on_settings)
    language_button.Bind(wx.EVT_BUTTON, _on_language_button)

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

    frame._wx_shell_controls = {"version": version_label, "update": update_btn, "plugins": plugins_btn, "send_logs": send_logs_btn, "settings": settings_btn, "help": help_btn, "language_button": language_button, "menu": menu, "language_menu": language_menu, "language_items": language_items, "notebook": notebook, "pages": page_controls}
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


def main() -> int:
    clean_environment = environment_without_qt_graphics()
    for name in set(os.environ) - set(clean_environment):
        os.environ.pop(name, None)
    load_saved_language(system_default_language())
    import wx

    app = wx.App(False)

    # --- Startup splash per spec §18-29: Preferences → Helpers → Updates → Session → Main Window ---
    # The splash is shown before the main window is built, with real startup workflow visible.
    from hpc_gui.config.storage import load_profiles

    profiles = []
    try:
        profiles = load_profiles()
    except Exception:
        profiles = []

    # Create splash early to paint before heavy init
    splash = None
    try:
        from hpc_gui.wx_splash import create_startup_splash, STATE_ACTIVE, STATE_COMPLETE, STATE_FAILED, STATE_PENDING

        splash = create_startup_splash(None, profiles=profiles)
        splash.Show()
        try:
            splash.Update()
        except Exception:
            pass
        app.Yield(True)
        # Phase: Preferences
        splash._wx_splash_set_stage("preferences", STATE_ACTIVE)
        splash._wx_splash_set_progress(10, t("splash.loading_preferences") if t("splash.loading_preferences") != "[splash.loading_preferences]" else "Loading preferences...")
        splash._wx_splash_append_log("Loading preferences...", "OK")
        app.Yield(True)
        wx.MilliSleep(80)
        splash._wx_splash_set_stage("preferences", STATE_COMPLETE)
        # Phase: Helpers
        splash._wx_splash_set_stage("helpers", STATE_ACTIVE)
        splash._wx_splash_set_progress(35, t("splash.checking_helpers") if t("splash.checking_helpers") != "[splash.checking_helpers]" else "Checking SSH and SFTP helpers...")
        splash._wx_splash_append_log("Checking SSH helper...", "OK")
        splash._wx_splash_append_log("Checking SFTP helper...", "OK")
        app.Yield(True)
        wx.MilliSleep(80)
        splash._wx_splash_set_stage("helpers", STATE_COMPLETE)
        # Phase: Updates
        splash._wx_splash_set_stage("updates", STATE_ACTIVE)
        splash._wx_splash_set_progress(60, t("splash.checking_updates") if t("splash.checking_updates") != "[splash.checking_updates]" else "Checking for updates...")
        splash._wx_splash_append_log("Checking for updates...", "")
        app.Yield(True)
        wx.MilliSleep(80)
        # Best-effort update check without blocking startup (real check happens in main window)
        splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        # Phase: Session
        splash._wx_splash_set_stage("session", STATE_ACTIVE)
        splash._wx_splash_set_progress(85, t("splash.loading_session") if t("splash.loading_session") != "[splash.loading_session]" else "Loading connection profiles...")
        splash._wx_splash_append_log("Loading connection profiles...", "OK")
        app.Yield(True)
        wx.MilliSleep(80)
    except Exception:
        # Splash is best-effort; continue without it
        splash = None

    frame, _lifecycle, _session_state = create_shell_frame(app)
    # Wire splash connection controls to real session
    if splash is not None:
        try:
            # Reload
            reload_btn = splash._wx_splash_controls.get("reload")
            if reload_btn is not None:
                def _splash_reload(_evt=None, _splash=splash):
                    try:
                        from hpc_gui.config.storage import load_profiles as _lp
                        new_profiles = _lp()
                        choice = _splash._wx_splash_controls.get("profile_choice")
                        if choice is not None and new_profiles:
                            choice.Clear()
                            for p in new_profiles:
                                if p.get("name"):
                                    choice.Append(str(p.get("name")))
                            if choice.GetCount():
                                choice.SetSelection(0)
                            _splash._wx_splash_append_log("Reloaded connection profiles", "OK")
                    except Exception as exc:
                        _splash._wx_splash_append_log(f"Reload failed: {exc}", "")
                reload_btn.Bind(wx.EVT_BUTTON, _splash_reload)

            # Connect Selected wiring — delegates to connection controller
            connect_btn = splash._wx_splash_controls.get("connect")
            if connect_btn is not None:
                def _splash_connect(_evt=None, _splash=splash, _frame=frame, _lc=_lifecycle, _ss=_session_state):
                    sel = ""
                    try:
                        sel = _splash._wx_splash_controls["profile_choice"].GetStringSelection()
                    except Exception:
                        sel = ""
                    _splash._wx_splash_set_connecting(True, sel)
                    # Perform connection via shared helper
                    def worker():
                        try:
                            from hpc_gui.config.storage import load_profiles as _lp
                            profiles_now = _lp()
                            profile = next((p for p in profiles_now if str(p.get("name")) == sel), None)
                            if profile is None:
                                raise RuntimeError(t("login.error"))
                            # Use WxConnectionModel path
                            from hpc_gui.wx_connection import WxConnectionModel, connect_profile
                            model = WxConnectionModel(profiles_now)
                            model.select(sel)
                            # Connect using shared logic (may show host-key dialogs parented to splash)
                            session = connect_profile(profile, model)
                            def on_done():
                                try:
                                    _frame._wx_shell_session_state["session"] = session
                                    _frame._wx_shell_session_state["generation"] = _frame._wx_shell_session_state.get("generation", 0) + 1
                                    # sync terminal
                                    try:
                                        panel = _frame._wx_shell_session_state.get("_embedded_terminal_panel")
                                        if panel is not None and hasattr(panel, "_wx_terminal_set_ssh"):
                                            panel._wx_terminal_set_ssh(session.get("ssh"))
                                    except Exception:
                                        pass
                                    _splash._wx_splash_append_log(f"Connected to {sel}", "OK")
                                    _splash._wx_splash_set_stage("session", STATE_COMPLETE)
                                    _splash._wx_splash_set_progress(100, t("common.ready") if t("common.ready") != "[common.ready]" else "Ready")
                                    wx.CallLater(300, lambda: (_splash.EndModal(wx.ID_OK) if _splash.IsModal() else _splash.Close()))
                                    _frame.Show()
                                    _frame.Raise()
                                except Exception:
                                    pass
                            wx.CallAfter(on_done)
                        except Exception as exc:
                            def on_err():
                                _splash._wx_splash_set_connecting(False, sel)
                                _splash._wx_splash_append_log(f"Connection failed: {exc}", "")
                                _splash._wx_splash_set_stage("session", STATE_FAILED)
                            wx.CallAfter(on_err)
                    Thread(target=worker, daemon=True).start()
                # Re-bind to our handler (override default no-op)
                try:
                    connect_btn.Unbind(wx.EVT_BUTTON)
                except Exception:
                    pass
                connect_btn.Bind(wx.EVT_BUTTON, _splash_connect)

            # Continue Offline wiring
            offline_btn = splash._wx_splash_controls.get("offline")
            if offline_btn is not None:
                def _splash_offline(_evt=None, _splash=splash, _frame=frame):
                    _splash._wx_splash_set_offline()
                    _splash._wx_splash_append_log("Starting in offline mode...", "")
                    def close_splash():
                        try:
                            if _splash.IsModal():
                                _splash.EndModal(wx.ID_CANCEL)
                            else:
                                _splash.Close()
                        except Exception:
                            pass
                        _frame.Show()
                        _frame.Raise()
                    wx.CallLater(300, close_splash)
                try:
                    offline_btn.Unbind(wx.EVT_BUTTON)
                except Exception:
                    pass
                offline_btn.Bind(wx.EVT_BUTTON, _splash_offline)

            # Show dialog modally with connection controls ready; main frame hidden until decision
            frame.Hide()
            result = splash.ShowModal()
            # If splash closed via Connect success, frame already shown; otherwise show frame
            if not frame.IsShown():
                frame.Show()
            try:
                splash.Destroy()
            except Exception:
                pass
            # Mark Session stage complete or offline as appropriate
            try:
                if result == wx.ID_CANCEL:
                    # Continue Offline path — session remains None, UI shows offline states
                    pass
            except Exception:
                pass
        except Exception:
            try:
                splash.Destroy()
            except Exception:
                pass
            frame.Show()
    else:
        frame.Show()

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


def _start_file_transfers(session_state, lifecycle, items, *, on_progress=None, conflict_resolver=None, files_backend=None, parent=None):
    """Queue file-view transfers through the shared transfer lifecycle."""
    from hpc_gui.wx_transfer_workspace import create_transfer_progress

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
        if item.op == "upload":
            method = files.resume_upload if conflict_decision == "resume" else files.upload
            method(item.src, item.dst)
        elif item.op == "download":
            method = files.resume_download if conflict_decision == "resume" else files.download
            method(item.src, item.dst)
        else:
            raise RuntimeError(f"unsupported transfer item: {item.op}")
        progress(1, 1)

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

    controller = TransferSessionController(
        items,
        run_item,
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
    _snapshot_session = (session_state or {}).get("session") or {}
    _snapshot_files = _snapshot_session.get("files")
    _manager = _get_editor_manager(session_state, parent, lifecycle)

    def remote_operation(action, paths, destination=""):
        session = (session_state or {}).get("session") or {}
        files = _snapshot_files if _snapshot_files is not None else session.get("files")
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
        raise RuntimeError(f"Remote action is not available from this view: {action}")

    def _editor(path, content="", request_id=None):
        _manager.open_primary(path, content, is_local=False, request_id=request_id)

    _editor._wx_request_aware = True

    def _editor_request_started():
        return _manager.begin_primary_request()

    _editor._wx_request_started = _editor_request_started

    def _editor_new_window(path, content=""):
        _manager.open_new_window(path, content, is_local=False)

    def _loader(path):
        session = (session_state or {}).get("session") or {}
        files = _snapshot_files if _snapshot_files is not None else session.get("files")
        if files and hasattr(files, "iterdir_entries"):
            return files.iterdir_entries(path)
        return ()

    def _read_text(path):
        session = (session_state or {}).get("session") or {}
        files = _snapshot_files if _snapshot_files is not None else session.get("files")
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

    # Only provide loader/read_text if there is a session; otherwise return None-like behavior
    # The panel will handle None by not loading, but we provide dynamic functions so embedded
    # panel works after connection. Check session at call time inside loader already.
    return {
        "loader": loader,
        "read_text": read_text,
        "operation": remote_operation,
        "open_editor": _editor,
        "open_editor_new_window": _editor_new_window,
        "run_shell": lambda path: _run_shell_in_terminal(session_state, parent, lifecycle, [path]),
    }


def _jobs_callbacks(session_state, parent, lifecycle):
    _snapshot_session = (session_state or {}).get("session") or {}
    _snapshot_slurm = _snapshot_session.get("slurm")
    _snapshot_profile = _snapshot_session.get("profile")
    _snapshot_files = _snapshot_session.get("files")

    def list_jobs():
        session = (session_state or {}).get("session") or {}
        slurm = _snapshot_slurm if _snapshot_slurm is not None else session.get("slurm")
        profile = _snapshot_profile if _snapshot_profile is not None else session.get("profile") or {}
        if not slurm:
            return ()
        raw = slurm.squeue(str(profile.get("username", "")))
        rows = []
        for line in str(raw or "").splitlines()[1:]:
            fields = line.split()
            if fields:
                rows.append({"id": fields[0], "state": fields[4] if len(fields) > 4 else "", "name": fields[2] if len(fields) > 2 else ""})
        return rows

    def read_output(job_id):
        session = (session_state or {}).get("session") or {}
        slurm = _snapshot_slurm if _snapshot_slurm is not None else session.get("slurm")
        files = _snapshot_files if _snapshot_files is not None else session.get("files")
        if not slurm or not files:
            return {}
        metadata = str(slurm.scontrol_show_job(job_id) or "")
        paths = {key: next((part.split("=", 1)[1] for part in metadata.split() if part.startswith(f"{key}=")), "") for key in ("StdOut", "StdErr")}
        return {"stdout": files.read_text(paths["StdOut"]) if paths["StdOut"] else "", "stderr": files.read_text(paths["StdErr"]) if paths["StdErr"] else ""}

    def list_job_files(job_id):
        # test seam
        test_files = session_state.get("_test_job_files")
        if test_files is not None:
            # allow per-job mapping or single list
            if isinstance(test_files, dict):
                return tuple(test_files.get(str(job_id), ()))
            return tuple(test_files)
        session = (session_state or {}).get("session") or {}
        slurm = _snapshot_slurm if _snapshot_slurm is not None else session.get("slurm")
        files = _snapshot_files if _snapshot_files is not None else session.get("files")
        if not slurm or not files or not hasattr(files, "iterdir_entries"):
            return ()
        try:
            meta = str(slurm.scontrol_show_job(job_id) or "")
            # try WorkDir, else StdOut dir
            workdir = ""
            for part in meta.split():
                if part.startswith("WorkDir="):
                    workdir = part.split("=",1)[1]
                    break
            if not workdir:
                # fallback to StdOut dirname
                for part in meta.split():
                    if part.startswith("StdOut="):
                        p = part.split("=",1)[1]
                        workdir = str(PurePosixPath(p).parent) if p else ""
                        break
            if not workdir:
                return ()
            return tuple(files.iterdir_entries(workdir))
        except Exception:
            return ()

    def _cancel(job_id):
        session = (session_state or {}).get("session") or {}
        slurm = _snapshot_slurm if _snapshot_slurm is not None else session.get("slurm")
        if slurm and hasattr(slurm, "scancel"):
            return slurm.scancel(job_id)
        return None

    def _final_state(job_id):
        session = (session_state or {}).get("session") or {}
        slurm = _snapshot_slurm if _snapshot_slurm is not None else session.get("slurm")
        if slurm and hasattr(slurm, "job_state"):
            return slurm.job_state(job_id)
        return ""

    return {
        "list_jobs": list_jobs,
        "read_output": read_output,
        "list_job_files": list_job_files,
        "cancel": _cancel,
        "final_state": _final_state,
        "generation": lambda: session_state.get("generation", 0),
        "lifecycle": lifecycle,
    }


def _connection_callbacks(session_state, parent, lifecycle):
    from hpc_gui.config.storage import load_profiles

    profiles = load_profiles()

    def on_connected(session):
        session_state["session"] = session
        session_state["generation"] = session_state.get("generation", 0) + 1
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

    return {"profiles": profiles, "lifecycle": lifecycle, "on_connected": on_connected}


def _logs_callbacks(session_state, parent, lifecycle):
    # Logs view uses WxLogsModel internally; no session needed
    return {}


def _directories_callbacks(session_state, parent, lifecycle):
    # Share single implementation between embedded tab and dispatch
    # Pass session_state so view can derive scratch/home via system_profile helpers
    # Also provide run_shell delegation matching _remote_files_callbacks pattern
    return {"session_state": session_state}


def _dispatch(command_id: str, parent=None, lifecycle=None, session_state=None) -> None:
    if command_id in {"APP-HELP", "APP-COMMAND-PALETTE"}:
        from hpc_gui.wx_help import show_help

        show_help(parent)
    elif command_id == "APP-CONNECT":
        from hpc_gui.wx_connection import show_connection

        _conn = _connection_callbacks(session_state, parent, lifecycle)
        show_connection(parent, **_conn)
    elif command_id == "NAV-FILES":
        from hpc_gui.wx_local_files import show_local_files

        _kwargs = _local_files_callbacks(session_state, parent, lifecycle)
        show_local_files(parent, **_kwargs)
    elif command_id == "NAV-DIRECTORIES":
        from hpc_gui.wx_directories_view import show_directories

        show_directories(parent, **_directories_callbacks(session_state, parent, lifecycle))
    elif command_id == "NAV-LOGS":
        from hpc_gui.wx_logs_view import show_logs

        _kwargs = _logs_callbacks(session_state, parent, lifecycle)
        show_logs(parent, **_kwargs)
    elif command_id == "NAV-EDITOR":
        _get_editor_manager(session_state, parent, lifecycle).open_primary("", "", is_local=False)
    elif command_id == "NAV-TERMINAL":
        from hpc_gui.wx_terminal import show_terminal

        session = (session_state or {}).get("session") or {}
        show_terminal(parent, ssh=session.get("ssh"), lifecycle=lifecycle)
    elif command_id == "NAV-JOBS":
        from hpc_gui.wx_jobs import show_jobs

        _kwargs = _jobs_callbacks(session_state, parent, lifecycle)
        # show_jobs expects lifecycle, list_jobs, read_output, cancel, final_state, generation
        show_jobs(parent, **_kwargs)
    elif command_id in {"PLUGIN-ANSYS-LINTER", "APP-ANSYS"}:
        from hpc_gui.wx_ansys_view import show_ansys_lint

        show_ansys_lint(parent, lifecycle=lifecycle)


__all__ = ["main"]
