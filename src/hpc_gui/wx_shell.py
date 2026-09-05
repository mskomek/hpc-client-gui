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
    frame = wx.Frame(None, title=f"HPC Client GUI {__version__}", size=(960, 640))
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
    # --- chrome row (Qt order, top-right, above notebook) ---
    chrome_sizer = wx.BoxSizer(wx.HORIZONTAL)
    version_label = wx.StaticText(panel, label=f"v{__version__}")
    update_btn = wx.Button(panel, label=t("updates.action"))
    plugins_btn = wx.Button(panel, label=t("plugins.action"))
    send_logs_btn = wx.Button(panel, label=t("crash.send_logs_btn"))
    settings_btn = wx.Button(panel, label=t("settings.action"))
    help_btn = wx.Button(panel, label=t("help.help_title"))
    cur_lang = current_language()
    language_button = wx.Button(panel, label=t("language.english") if cur_lang == "en" else t("language.turkish"))
    try:
        language_button.SetBitmap(_flag_bitmap(wx, cur_lang))
    except Exception:
        pass
    chrome_sizer.AddStretchSpacer(1)
    chrome_sizer.Add(version_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
    chrome_sizer.Add(update_btn, 0, wx.ALL, 4)
    chrome_sizer.Add(plugins_btn, 0, wx.ALL, 4)
    chrome_sizer.Add(send_logs_btn, 0, wx.ALL, 4)
    chrome_sizer.Add(settings_btn, 0, wx.ALL, 4)
    chrome_sizer.Add(help_btn, 0, wx.ALL, 4)
    chrome_sizer.Add(language_button, 0, wx.ALL, 4)
    root.Add(chrome_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
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

    # Files (splitter with local left, remote right)
    splitter = wx.SplitterWindow(notebook)
    _local = _local_files_callbacks(session_state, frame, lifecycle)
    _remote = _remote_files_callbacks(session_state, frame, lifecycle)
    local_panel = build_local_files_panel(splitter, **_local)
    remote_panel = build_remote_files_panel(splitter, **_remote)
    splitter.SplitVertically(local_panel, remote_panel, 300)
    splitter.SetMinimumPaneSize(200)
    notebook.AddPage(splitter, t("tabs.ftp"), False)
    page_controls["NAV-FILES"] = {"page": splitter, "local": local_panel, "remote": remote_panel}

    # Script Editor
    _editor_kwargs = {"action_factory": _editor_action_factory(session_state)}
    editor_panel = build_editor_panel(notebook, **_editor_kwargs)
    notebook.AddPage(editor_panel, t("tabs.editor"), False)
    page_controls["NAV-EDITOR"] = {"page": editor_panel}

    # Terminal (existing page, unchanged)
    terminal_page = wx.Panel(notebook)
    terminal_sizer = wx.BoxSizer(wx.VERTICAL)
    terminal_output = wx.TextCtrl(terminal_page, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    terminal_input = wx.TextCtrl(terminal_page, style=wx.TE_PROCESS_ENTER)
    terminal_sizer.Add(terminal_output, 1, wx.EXPAND | wx.ALL, 8)
    terminal_sizer.Add(terminal_input, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    terminal_page.SetSizer(terminal_sizer)
    notebook.AddPage(terminal_page, t("help.section_terminal"), False)
    page_controls["NAV-TERMINAL"] = {"page": terminal_page, "output": terminal_output, "input": terminal_input}

    # Logs
    _logs = _logs_callbacks(session_state, frame, lifecycle)
    logs_panel = build_logs_panel(notebook, **_logs)
    notebook.AddPage(logs_panel, t("tabs.logs"), False)
    page_controls["NAV-LOGS"] = {"page": logs_panel}
    root.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(root)
    frame.CreateStatusBar()
    frame.SetStatusText(t("common.ready"))

    def send_terminal_input(event):
        session = session_state.get("session") or {}
        ssh = session.get("ssh")
        value = terminal_input.GetValue()
        if ssh and value:
            ssh.send_shell_input(value + "\n")
            terminal_input.Clear()
        elif not ssh:
            terminal_output.AppendText(t("login.status_disconnected") + "\n")
        event.Skip()

    terminal_input.Bind(wx.EVT_TEXT_ENTER, send_terminal_input)

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

        def worker():
            try:
                from hpc_gui.services.app_updater import get_latest_release, is_newer_version
                from hpc_gui import __version__ as cur_ver
                release = get_latest_release()

                def on_done():
                    ff = _shell_frame()
                    if not ff:
                        return
                    try:
                        if not wx.Window.FindWindowById(ff.GetId()):
                            return
                    except Exception:
                        return
                    try:
                        if not is_newer_version(release.version, cur_ver):
                            wx.MessageBox(t("updates.up_to_date").format(version=cur_ver), t("updates.title"), wx.OK | wx.ICON_INFORMATION, ff)
                            _track_new_windows(before)
                            return
                        choice = wx.MessageBox(t("updates.available_message").format(current=cur_ver, latest=release.version), t("updates.available_title"), wx.YES_NO | wx.ICON_QUESTION, ff)
                        _track_new_windows(before)
                    except Exception as exc:
                        try:
                            wx.MessageBox(str(exc), t("updates.error_title"), wx.OK | wx.ICON_ERROR, ff)
                        except Exception:
                            pass

                wx.CallAfter(on_done)
            except Exception as exc:
                def on_err():
                    ff = _shell_frame()
                    if not ff:
                        return
                    try:
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
            # For Files splitter, local/remote are stored separately
            candidates = []
            if "page" in controls:
                candidates.append(controls["page"])
            if "local" in controls:
                candidates.append(controls["local"])
            if "remote" in controls:
                candidates.append(controls["remote"])
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
    frame, _lifecycle, _session_state = create_shell_frame(app)
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
    if parent:
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


__all__ = ["main"]
