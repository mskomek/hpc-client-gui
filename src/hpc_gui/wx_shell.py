"""Optional wxPython migration shell; Qt remains the default runtime."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from threading import Thread

from hpc_gui import __version__
from hpc_gui.core.i18n import load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change
from hpc_gui.services.command_registry import COMMAND_REGISTRY
from hpc_gui.wx_lifecycle import WxLifecycleController
from hpc_gui.wx_runtime import environment_without_qt_graphics


def main() -> int:
    clean_environment = environment_without_qt_graphics()
    for name in set(os.environ) - set(clean_environment):
        os.environ.pop(name, None)
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed; use the default Qt runtime") from exc
    load_saved_language(system_default_language())
    app = wx.App(False)
    lifecycle = WxLifecycleController()
    session_state = {"session": None}
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
        item = language_menu.Append(wx.ID_ANY, t(f"help.{key}"))
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
        frame.GetMenuBar().SetLabelTop(0, t("help.help_title"))
        frame.GetMenuBar().SetLabelTop(1, t("help.language"))
        for command, item in command_items:
            menu.SetLabel(item.GetId(), command.label())
        for language, item in language_items.items():
            language_menu.SetLabel(item.GetId(), t("help.english" if language == "en" else "help.turkish"))

    subscribe_language_change(refresh_labels)

    tray = None
    try:
        import wx.adv

        class TrayIcon(wx.adv.TaskBarIcon):
            def CreatePopupMenu(self):
                menu = wx.Menu()
                close = menu.Append(wx.ID_EXIT, "Exit")
                self.Bind(wx.EVT_MENU, lambda _event: frame.Close(), close)
                return menu

        tray = TrayIcon()
        tray.SetIcon(wx.ArtProvider.GetIcon(wx.ART_INFORMATION), "HPC Client GUI")
        lifecycle.set_tray_notifier(lambda message: tray.ShowBalloon(t("login.job_notification_title"), message, 5000))
    except (ImportError, RuntimeError):
        pass

    def close(_event):
        unsubscribe_language_change(refresh_labels)
        lifecycle.set_tray_notifier(None)
        lifecycle.shutdown()
        if tray:
            tray.Destroy()
        frame.Destroy()

    frame.Bind(wx.EVT_CLOSE, close)
    frame.Show()
    app.MainLoop()
    return 0


def _dispatch(command_id: str, parent=None, lifecycle=None, session_state=None) -> None:
    if command_id in {"APP-HELP", "APP-COMMAND-PALETTE"}:
        from hpc_gui.wx_help import show_help

        show_help(parent)
    elif command_id == "APP-CONNECT":
        from hpc_gui.config.storage import load_profiles
        from hpc_gui.wx_connection import show_connection

        def connected(session):
            session_state["session"] = session
            ssh = session.get("ssh") if isinstance(session, dict) else None
            if ssh is not None and callable(getattr(ssh, "close", None)):
                lifecycle.register_cleanup(ssh.close)

        show_connection(parent, load_profiles(), lifecycle=lifecycle, on_connected=connected)
    elif command_id == "NAV-FILES":
        from hpc_gui.wx_local_files import show_local_files
        from hpc_gui.wx_editor_view import show_editor

        def open_local(path, new_window=False):
            def worker():
                try:
                    content = Path(path).read_text(encoding="utf-8")
                    wx.CallAfter(show_editor, parent, path=path, content=content)
                except Exception as error:
                    wx.CallAfter(wx.MessageBox, str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)

            import wx

            Thread(target=worker, daemon=True).start()

        show_local_files(parent, open_editor=lambda path: open_local(path), open_editor_new_window=lambda path: open_local(path, True))
    elif command_id == "NAV-DIRECTORIES":
        from hpc_gui.wx_editor_view import show_editor
        from hpc_gui.wx_remote_files_view import show_remote_files

        session = (session_state or {}).get("session") or {}
        files = session.get("files")
        slurm = session.get("slurm")
        ssh = session.get("ssh")
        def editor(path, content=""):
            show_editor(
                parent,
                path=path,
                content=content,
                save_remote=files.write_text if files else None,
                on_submit=(lambda document: slurm.sbatch(document.path)) if slurm else None,
                on_run=(lambda document: ssh.send_shell_text(f"bash -- {shlex.quote(document.path)}\n")) if ssh else None,
            )
        show_remote_files(
            parent,
            loader=files.iterdir_entries if files else None,
            read_text=files.read_text if files else None,
            open_editor=editor,
            open_editor_new_window=editor,
        )
    elif command_id == "NAV-EDITOR":
        from hpc_gui.wx_editor_view import show_editor

        session = (session_state or {}).get("session") or {}
        files = session.get("files")
        slurm = session.get("slurm")
        ssh = session.get("ssh")
        show_editor(
            parent,
            save_remote=files.write_text if files else None,
            on_submit=(lambda document: slurm.sbatch(document.path)) if slurm else None,
            on_run=(lambda document: ssh.send_shell_text(f"bash -- {shlex.quote(document.path)}\n")) if ssh else None,
        )
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

        show_jobs(parent, lifecycle=lifecycle, list_jobs=list_jobs, read_output=read_output, cancel=slurm.scancel if slurm else None)


__all__ = ["main"]
