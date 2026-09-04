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
    title_label = wx.StaticText(panel, label=f"HPC Client GUI {__version__}")
    description_label = wx.StaticText(panel, label=t("help.wx_shell_description"))
    root.Add(title_label, 0, wx.ALL, 12)
    root.Add(description_label, 0, wx.LEFT | wx.BOTTOM, 12)
    panel.SetSizer(root)
    frame.CreateStatusBar()
    frame.SetStatusText(t("common.ready"))

    def refresh_labels(_language=None):
        frame.SetTitle(f"{t('app.title')} {__version__}")
        title_label.SetLabel(f"{t('app.title')} {__version__}")
        description_label.SetLabel(t("help.wx_shell_description"))
        frame.SetStatusText(t("common.ready"))
        frame.GetMenuBar().SetMenuLabel(0, t("help.help_title"))
        frame.GetMenuBar().SetMenuLabel(1, t("help.language"))
        for command, item in command_items:
            menu.SetLabel(item.GetId(), command.label())
        for language, item in language_items.items():
            language_menu.SetLabel(item.GetId(), t("help.english" if language == "en" else "help.turkish"))
            item.Check(current_language() == language)

    subscribe_language_change(refresh_labels)

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

    frame._wx_shell_controls = {"title": title_label, "description": description_label, "menu": menu, "language_menu": language_menu, "language_items": language_items}
    frame._wx_shell_lifecycle = lifecycle
    frame._wx_shell_session_state = session_state
    frame._wx_shell_tray = tray

    def close(_event):
        unsubscribe_language_change(refresh_labels)
        lifecycle.set_tray_notifier(None)
        frame.Hide()
        for child in wx.GetTopLevelWindows():
            if child is not frame and child.GetParent() is frame:
                child.Close()
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

    show_terminal(parent, ssh=ssh, lifecycle=lifecycle)
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


def _dispatch(command_id: str, parent=None, lifecycle=None, session_state=None) -> None:
    if command_id in {"APP-HELP", "APP-COMMAND-PALETTE"}:
        from hpc_gui.wx_help import show_help

        show_help(parent)
    elif command_id == "APP-CONNECT":
        from hpc_gui.config.storage import load_profiles
        from hpc_gui.wx_connection import show_connection

        def connected(session):
            session_state["session"] = session
            session_state["generation"] = session_state.get("generation", 0) + 1
            ssh = session.get("ssh") if isinstance(session, dict) else None
            if ssh is not None and callable(getattr(ssh, "close", None)):
                lifecycle.register_cleanup(ssh.close)

        show_connection(parent, load_profiles(), lifecycle=lifecycle, on_connected=connected)
    elif command_id == "NAV-FILES":
        from hpc_gui.wx_local_files import show_local_files
        session = (session_state or {}).get("session") or {}
        files = session.get("files")

        editor_manager = _get_editor_manager(session_state, parent, lifecycle)

        def open_local(path, new_window=False):
            request_id = None if new_window else editor_manager.begin_primary_request()
            def worker():
                try:
                    content = Path(path).read_text(encoding="utf-8")
                    opener = editor_manager.open_new_window if new_window else editor_manager.open_primary
                    if new_window:
                        wx.CallAfter(opener, path, content, is_local=True)
                    else:
                        wx.CallAfter(opener, path, content, is_local=True, request_id=request_id)
                except Exception as error:
                    wx.CallAfter(wx.MessageBox, str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)

            import wx

            Thread(target=worker, daemon=True).start()

        def upload_local(paths):
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
                    wx.CallAfter(wx.MessageBox, str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)

            Thread(target=worker, daemon=True).start()

        show_local_files(
            parent,
            open_editor=lambda path: open_local(path),
            open_editor_new_window=lambda path: open_local(path, True),
            upload=upload_local,
            run_shell=lambda path: _run_shell_in_terminal(session_state, parent, lifecycle, [path]),
        )
    elif command_id == "NAV-DIRECTORIES":
        from hpc_gui.wx_remote_files_view import show_remote_files

        session = (session_state or {}).get("session") or {}
        files = session.get("files")
        slurm = session.get("slurm")
        def remote_operation(action, paths, destination=""):
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
        def editor(path, content="", request_id=None):
            editor_manager.open_primary(path, content, is_local=False, request_id=request_id)

        editor._wx_request_aware = True

        def editor_request_started():
            return editor_manager.begin_primary_request()

        editor._wx_request_started = editor_request_started

        def editor_new_window(path, content=""):
            editor_manager.open_new_window(path, content, is_local=False)

        editor_manager = _get_editor_manager(session_state, parent, lifecycle)
        show_remote_files(
            parent,
            loader=files.iterdir_entries if files else None,
            read_text=files.read_text if files else None,
            operation=remote_operation,
            open_editor=editor,
            open_editor_new_window=editor_new_window,
            run_shell=lambda path: _run_shell_in_terminal(session_state, parent, lifecycle, [path]),
        )
    elif command_id == "NAV-EDITOR":
        _get_editor_manager(session_state, parent, lifecycle).open_primary("", "", is_local=False)
    elif command_id == "NAV-TERMINAL":
        from hpc_gui.wx_terminal import show_terminal

        session = (session_state or {}).get("session") or {}
        show_terminal(parent, ssh=session.get("ssh"), lifecycle=lifecycle)
    elif command_id == "NAV-JOBS":
        from hpc_gui.wx_jobs import show_jobs

        session = (session_state or {}).get("session") or {}
        slurm = session.get("slurm")
        files = session.get("files")
        profile = session.get("profile") or {}

        def list_jobs():
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
            if not slurm or not files:
                return {}
            metadata = str(slurm.scontrol_show_job(job_id) or "")
            paths = {key: next((part.split("=", 1)[1] for part in metadata.split() if part.startswith(f"{key}=")), "") for key in ("StdOut", "StdErr")}
            return {"stdout": files.read_text(paths["StdOut"]) if paths["StdOut"] else "", "stderr": files.read_text(paths["StdErr"]) if paths["StdErr"] else ""}

        show_jobs(
            parent,
            lifecycle=lifecycle,
            list_jobs=list_jobs,
            final_state=slurm.job_state if slurm else None,
            generation=lambda: session_state.get("generation", 0),
            read_output=read_output,
            cancel=slurm.scancel if slurm else None,
        )


__all__ = ["main"]
