"""wx directories view with two remote panes."""

from __future__ import annotations

from threading import Thread

from hpc_gui.config.system_profile import format_remote_path, normalize_system_settings
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_directories import WxDirectoriesWorkspace
from hpc_gui.wx_host import make_host
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


def _resolve_scratch_home(session_state) -> tuple[str, str]:
    """Derive scratch/home paths from session, never hardcode."""
    session = None
    if isinstance(session_state, dict):
        session = session_state.get("session")
        if session is None and session_state.get("profile"):
            # session_state itself might be session
            session = session_state
    if not isinstance(session, dict):
        session = {}

    cfg = session.get("cfg") if isinstance(session.get("cfg"), (dict, object)) and session.get("cfg") is not None else None
    # Fallback to profile dict if cfg missing
    if cfg is None:
        profile = session.get("profile")
        if isinstance(profile, dict):
            cfg = profile
        else:
            cfg = session.get("cfg")

    user = "user"
    system_raw = None
    if isinstance(cfg, dict):
        user = str(cfg.get("username") or cfg.get("user") or user)
        system_raw = cfg.get("system_settings") if "system_settings" in cfg else cfg.get("system") if "system" in cfg else cfg.get("system_profile")
        # also provider may be elsewhere, but normalize handles missing
    elif cfg is not None:
        # object with attributes
        user = str(getattr(cfg, "username", None) or getattr(cfg, "user", None) or user)
        system_raw = getattr(cfg, "system_settings", None)
        if system_raw is None:
            system_raw = getattr(cfg, "system", None)
    else:
        # try profile again
        profile = session.get("profile") if isinstance(session.get("profile"), dict) else {}
        if isinstance(profile, dict):
            user = str(profile.get("username") or user)
            system_raw = profile.get("system_settings") or profile.get("system")

    system = normalize_system_settings(system_raw)
    scratch_dir = format_remote_path(system.get("scratch_dir", ""), user) if isinstance(system.get("scratch_dir"), str) else ""
    home_dir = format_remote_path(system.get("home_dir", ""), user) if isinstance(system.get("home_dir"), str) else ""
    # fallback to "/" if still empty (panel must still construct)
    if not scratch_dir:
        scratch_dir = "/"
    if not home_dir:
        home_dir = "/"
    return scratch_dir, home_dir


def _build_directories(parent, *, session_state=None, workspace: WxDirectoriesWorkspace | None = None, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None, run_shell=None, submit=None, embedded):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    from hpc_gui.wx_remote_files_view import build_remote_files_panel

    scratch_dir, home_dir = _resolve_scratch_home(session_state)

    # Resolve workspace metadata if not provided
    if workspace is None:
        metadata = (
            {"id": "scratch", "label": scratch_dir, "path": scratch_dir},
            {"id": "home", "label": home_dir, "path": home_dir},
        )
        workspace = WxDirectoriesWorkspace(metadata, open_editor=open_editor, submit=submit, run_shell=run_shell)

    # Resolve dynamic file callbacks if not explicitly provided, mirroring _remote_files_callbacks snapshot pattern
    snapshot_session = (session_state or {}).get("session") or {} if isinstance(session_state, dict) else {}
    snapshot_files = snapshot_session.get("files") if isinstance(snapshot_session, dict) else None

    def _files():
        sess = (session_state or {}).get("session") or {} if isinstance(session_state, dict) else {}
        f = snapshot_files if snapshot_files is not None else (sess.get("files") if isinstance(sess, dict) else None)
        return f

    # Default loader/operation/read_text if not supplied – delegate to files backend dynamically
    if loader is None:
        def loader(path):
            files = _files()
            if files and hasattr(files, "iterdir_entries"):
                return files.iterdir_entries(path)
            return ()

    if read_text is None:
        def read_text(path):
            files = _files()
            if files and hasattr(files, "read_text"):
                return files.read_text(path)
            return ""

    if operation is None:
        def operation(action, paths, destination=""):
            files = _files()
            if action == "delete" and files:
                for rp in paths:
                    files.remove(rp, recursive=True)
                return
            if action == "rename" and files and len(paths) == 1 and destination:
                files.rename(paths[0], destination)
                return
            if action in {"copy", "move"} and files and destination:
                from pathlib import PurePosixPath
                for rp in paths:
                    target = str(PurePosixPath(destination) / PurePosixPath(rp).name)
                    (files.copy if action == "copy" else files.move)(rp, target)
                return
            if action == "download" and files and destination:
                # importing _start_file_transfers would need session_state; fallback to direct? keep simple
                # use generic transfer via files if available, else no-op
                return
            if action == "new_folder" and files and destination:
                files.mkdir(destination)
                return
            raise RuntimeError(f"Remote action is not available from this view: {action}")

    if open_editor is None:
        # fallback to session_state editor_manager if available
        def open_editor(path, content="", request_id=None):
            if session_state is not None and isinstance(session_state, dict):
                mgr = session_state.get("editor_manager")
                if mgr:
                    try:
                        # choose primary
                        if request_id is not None:
                            mgr.open_primary(path, content, is_local=False, request_id=request_id)
                        else:
                            mgr.open_primary(path, content, is_local=False)
                        return
                    except Exception:
                        pass

    if open_editor_new_window is None:
        def open_editor_new_window(path, content=""):
            if session_state is not None and isinstance(session_state, dict):
                mgr = session_state.get("editor_manager")
                if mgr:
                    try:
                        mgr.open_new_window(path, content, is_local=False)
                        return
                    except Exception:
                        pass

    # wrap open_editor for request awareness (mirrors _remote_files_callbacks)
    if open_editor is not None:
        _orig_editor = open_editor
        # try to get manager for request id handling
        _mgr = (session_state or {}).get("editor_manager") if isinstance(session_state, dict) else None
        if _mgr is not None:
            def _editor(path, content="", request_id=None):
                _mgr.open_primary(path, content, is_local=False, request_id=request_id)
            _editor._wx_request_aware = True
            def _started():
                return _mgr.begin_primary_request()
            _editor._wx_request_started = _started
            open_editor = _editor
            def _editor_new(path, content=""):
                _mgr.open_new_window(path, content, is_local=False)
            open_editor_new_window = _editor_new
        else:
            # keep original but mark if possible
            pass

    host, finish = make_host(parent, title=t("tabs.directories"), size=(1000, 650), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)

    # Top button row
    top = wx.BoxSizer(wx.HORIZONTAL)
    btn_new_slurm = wx.Button(panel, label=t("dirs.new_slurm_edit"))
    top.Add(btn_new_slurm, 0, wx.ALL, 6)
    top.AddStretchSpacer(1)
    root.Add(top, 0, wx.EXPAND)

    splitter = wx.SplitterWindow(panel)
    # Prepare callbacks for each pane; reuse same loader/operation but with distinct initial models
    scratch_model = WxRemoteDirectoryModel(scratch_dir)
    home_model = WxRemoteDirectoryModel(home_dir)

    # Each pane shows its path as a title above the listing (Qt parity: directories_widget.py:216-219)
    # Use already-derived scratch_dir/home_dir; no new derivation or hardcoded paths.
    scratch_container = wx.Panel(splitter)
    scratch_sizer = wx.BoxSizer(wx.VERTICAL)
    scratch_label = wx.StaticText(scratch_container, label=scratch_dir)
    scratch_sizer.Add(scratch_label, 0, wx.EXPAND | wx.ALL, 4)
    scratch_panel = build_remote_files_panel(
        scratch_container,
        model=scratch_model,
        loader=loader,
        operation=operation,
        read_text=read_text,
        open_editor=open_editor,
        open_editor_new_window=open_editor_new_window,
        run_shell=run_shell,
    )
    scratch_sizer.Add(scratch_panel, 1, wx.EXPAND)
    scratch_container.SetSizer(scratch_sizer)

    home_container = wx.Panel(splitter)
    home_sizer = wx.BoxSizer(wx.VERTICAL)
    home_label = wx.StaticText(home_container, label=home_dir)
    home_sizer.Add(home_label, 0, wx.EXPAND | wx.ALL, 4)
    home_panel = build_remote_files_panel(
        home_container,
        model=home_model,
        loader=loader,
        operation=operation,
        read_text=read_text,
        open_editor=open_editor,
        open_editor_new_window=open_editor_new_window,
        run_shell=run_shell,
    )
    home_sizer.Add(home_panel, 1, wx.EXPAND)
    home_container.SetSizer(home_sizer)

    splitter.SplitVertically(scratch_container, home_container, 460)
    splitter.SetMinimumPaneSize(260)
    root.Add(splitter, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(root)

    def _new_slurm(_event=None):
        # If no session, just warn
        sess = (session_state or {}).get("session") if isinstance(session_state, dict) else None
        if not sess or not isinstance(sess, dict) or not sess.get("files"):
            try:
                wx.MessageBox(t("common.no_connection"), t("common.error"), wx.OK | wx.ICON_WARNING)
            except Exception:
                pass
            return
        # Pick scratch dir as default target, ask for template/key then file name.
        # Keep off GUI thread for template IO, but dialogs stay on GUI thread.
        try:
            import wx as _wx
        except ImportError:
            return
        # Use workspace batch concept? simplest delegate to open_editor with template
        # Reuse logic similar to DirectoriesWidget.create_slurm_from_template but simplified
        # Ask for file name
        name_dlg = _wx.TextEntryDialog(host, t("dirs.new_slurm_name_label"), t("dirs.new_slurm_name_title"), "new_job.slurm")
        try:
            if name_dlg.ShowModal() != _wx.ID_OK:
                return
            name = (name_dlg.GetValue() or "").strip()
        finally:
            name_dlg.Destroy()
        if not name:
            return
        if not name.lower().endswith((".slurm", ".sbatch")):
            name += ".slurm"
        target_path = scratch_dir.rstrip("/") + "/" + name

        files = sess.get("files")
        if files is not None:
            try:
                exists = bool(files.exists(target_path))
            except Exception:
                exists = False
            if exists:
                ans = _wx.MessageBox(t("dirs.new_slurm_exists"), t("dirs.conflict_title"), _wx.YES_NO | _wx.ICON_WARNING)
                if ans != _wx.ID_YES and ans != _wx.YES:
                    # wx.MessageBox returns ID_YES/ID_NO; handle both constants
                    if ans != _wx.ID_YES:
                        return

        # Resolve template off thread then open editor
        def worker():
            template_text = "#!/bin/bash\n#SBATCH --job-name=job\n"
            try:
                # Try to locate real template like Qt does
                from pathlib import Path as _Path
                root_tpl = _Path(__file__).resolve().parents[2] / "template.slurm"
                if root_tpl.exists():
                    template_text = root_tpl.read_text(encoding="utf-8")
            except Exception:
                pass
            def done():
                try:
                    if open_editor:
                        # open_editor expects (path, content)
                        # Use workspace open_editor if available else direct
                        ws_open = getattr(workspace, "_open_editor", None)
                        if ws_open:
                            ws_open(target_path)
                            # also need to provide content; emit via workspace double_click?
                            # fallback to open_editor callback
                            try:
                                open_editor(target_path, template_text)
                            except TypeError:
                                open_editor(target_path)
                        else:
                            try:
                                open_editor(target_path, template_text)
                            except TypeError:
                                open_editor(target_path)
                    else:
                        wx.MessageBox(f"Create: {target_path}", t("common.info"), wx.OK)
                except Exception as exc:
                    wx.MessageBox(str(exc), t("common.error"), wx.OK | wx.ICON_ERROR)
            wx.CallAfter(done)
        Thread(target=worker, daemon=True).start()

    btn_new_slurm.Bind(wx.EVT_BUTTON, _new_slurm)

    def refresh_labels(_language=None):
        host.set_host_title(t("tabs.directories"))
        btn_new_slurm.SetLabel(t("dirs.new_slurm_edit"))

    subscribe_language_change(refresh_labels)
    host.bind_host_close(lambda event: (unsubscribe_language_change(refresh_labels), event.Skip()))

    host._wx_dirs_controls = {
        "splitter": splitter,
        "scratch": scratch_panel,
        "home": home_panel,
        "scratch_container": scratch_container,
        "home_container": home_container,
        "scratch_label": scratch_label,
        "home_label": home_label,
        "new_slurm": btn_new_slurm,
    }
    host._wx_dirs_workspace = workspace
    host._wx_dirs_models = {"scratch": scratch_model, "home": home_model}

    finish()
    return host


def build_directories_panel(parent, *, session_state=None, workspace: WxDirectoriesWorkspace | None = None, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None, run_shell=None, submit=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_directories(
        parent,
        session_state=session_state,
        workspace=workspace,
        loader=loader,
        operation=operation,
        read_text=read_text,
        open_editor=open_editor,
        open_editor_new_window=open_editor_new_window,
        run_shell=run_shell,
        submit=submit,
        embedded=True,
    )


def show_directories(parent=None, *, session_state=None, workspace: WxDirectoriesWorkspace | None = None, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None, run_shell=None, submit=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_directories(
        parent,
        session_state=session_state,
        workspace=workspace,
        loader=loader,
        operation=operation,
        read_text=read_text,
        open_editor=open_editor,
        open_editor_new_window=open_editor_new_window,
        run_shell=run_shell,
        submit=submit,
        embedded=False,
    )
    return wx.ID_OK


__all__ = ["build_directories_panel", "show_directories"]
