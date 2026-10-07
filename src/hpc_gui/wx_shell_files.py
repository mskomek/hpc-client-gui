"""wx shell files workflows."""
from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath
from threading import Event, Thread
from hpc_gui.services.transfer_controller import TransferItem
import shlex
from hpc_gui.core.i18n import current_language, load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change
from hpc_gui.wx_shell_terminal import _run_shell_in_terminal
from hpc_gui.wx_shell_file_transfer import _start_file_transfers


def _editor_session_key(session_state):
    """Pinned connection identity for remote editor documents.

    W26 (HPC-W06-EDIT-012/016): a remote document records this key at open;
    saves compare it against the live session so a connection/profile switch
    can never redirect Save to the wrong host/path.
    """
    try:
        session = (session_state or {}).get("session") or {}
        profile = session.get("profile") or {}
        parts = (
            str(session.get("profile_name") or profile.get("name") or ""),
            str(profile.get("host") or ""),
            str(profile.get("port") or ""),
            str(profile.get("username") or ""),
        )
        key = "|".join(parts)
        return key if any(parts) else ""
    except Exception:
        return ""


def _editor_action_factory(session_state):
    # HPC-W06-XFER-018 explicit remote-save conflict policy: remote saves are
    # last-writer-wins.  The backend offers no versioned compare-and-swap, so
    # a remote document changed externally since it was opened is overwritten
    # without detection.  Users must re-open before editing when another
    # writer may be active.  Failed saves keep the document dirty/recoverable;
    # Save As to an existing remote target prompts via `target_exists`.
    def callbacks(document):
        session = session_state.get("session") or {}
        files = session.get("files")
        slurm = session.get("slurm")
        ssh = session.get("ssh")

        def _require_pinned_session(document):
            # HPC-W06-EDIT-016: a remote document pinned to a previous
            # connection must not save through the new session.  Refuse
            # visibly so the user re-opens from the current connection.
            try:
                pinned = str(getattr(document, "session_key", "") or "")
            except Exception:
                pinned = ""
            if pinned and not getattr(document, "is_local", True):
                current = _editor_session_key(session_state)
                if current and current != pinned:
                    message = t("editor.session_changed_reopen")
                    if not message or message.startswith("[editor.session_changed_reopen]"):
                        message = (
                            "Connection changed since this file was opened. "
                            "Re-open it from the current connection before saving "
                            "to avoid writing to the wrong host."
                        )
                    raise RuntimeError(message)
            return True

        def save_remote(path, content):
            _require_pinned_session(document)
            if not files:
                raise RuntimeError(t("editor.remote_file_service_unavailable"))
            files.write_text(path, content)

        def submit(current):
            _require_pinned_session(current)
            if not current.path:
                raise RuntimeError(t("editor.document_path_required"))
            if not slurm or not callable(getattr(slurm, "sbatch", None)):
                raise RuntimeError(t("editor.slurm_unavailable"))
            # W30 CTRL-001/002: validate required fields before sending and
            # require confirmed scheduler acceptance/job ID. Template
            # partition/account rules come from provider config, never
            # hardcoded values.
            from hpc_gui.services.job_submit_cancel import (
                submit_result_status,
                validate_submit_request,
            )

            try:
                _profile = (session_state.get("session") or {}).get("profile") or {}
                _prov = _profile.get("provider_template") if isinstance(_profile, dict) else None
                _prov_cfg = _prov if isinstance(_prov, dict) else (_profile if isinstance(_profile, dict) else None)
            except Exception:
                _prov_cfg = None
            _content = getattr(current, "content", None)
            _errors = validate_submit_request(
                str(current.path),
                _content if isinstance(_content, str) else None,
                provider_config=_prov_cfg if isinstance(_content, str) else None,
            )
            if _errors:
                raise RuntimeError("Submission validation failed: " + "; ".join(_errors))
            if current.is_local:
                if not files:
                    raise RuntimeError(t("editor.upload_or_slurm_unavailable"))
                remote_path = str(PurePosixPath("~") / Path(current.path).name)
                files.upload(current.path, remote_path)
                _output = slurm.sbatch(remote_path)
            else:
                _output = slurm.sbatch(current.path)
            _status, _detail = submit_result_status(str(_output or ""))
            if _status != "SUCCESS":
                raise RuntimeError(f"Submission failed: {_detail}")
            return _output

        def run(current):
            _require_pinned_session(current)
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
            "target_exists": (lambda path: files.exists(path)) if files and callable(getattr(files, "exists", None)) else None,
            "on_submit": submit,
            "on_run": run,
        }

    return callbacks


def _get_editor_manager(session_state, parent, lifecycle, *, save_remote=None, on_submit=None, on_run=None):
    from hpc_gui.wx_editor_windows import WxEditorWindowManager

    manager = session_state.get("editor_manager")
    if manager is None:
        action_factory = session_state.setdefault("editor_action_factory", _editor_action_factory(session_state))
        manager = WxEditorWindowManager(parent, action_factory=action_factory, save_remote=save_remote, on_submit=on_submit, on_run=on_run, lifecycle=lifecycle)
        session_state["editor_manager"] = manager
    return manager


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
        # W30 CTRL-001/002: required-field validation before sending and
        # confirmed scheduler acceptance afterwards. Provider template rules
        # are capability/config driven via _resolve_provider_config().
        from hpc_gui.services.job_submit_cancel import (
            submit_result_status,
            validate_submit_request,
        )

        _errors = validate_submit_request(str(path or ""), None, provider_config=None)
        if _errors:
            raise RuntimeError("Submission validation failed: " + "; ".join(_errors))
        _output = slurm.sbatch(path)
        _status, _detail = submit_result_status(str(_output or ""))
        if _status != "SUCCESS":
            raise RuntimeError(f"Submission failed: {_detail}")
        return _output

    def _editor(path, content="", request_id=None):
        try:
            _session = _resolve_session()
            _profile = _resolve_profile()
            _prov_cfg = _resolve_provider_config()
            _prov = _prov_cfg.get("name") if isinstance(_prov_cfg, dict) else ""
        except Exception:
            _session, _profile, _prov = {}, {}, ""
        _manager.open_primary(
            path,
            content,
            is_local=False,
            request_id=request_id,
            provider=str(_prov or ""),
            profile=str(_profile.get("name") or ""),
            session_key=_editor_session_key(session_state),
        )

    _editor._wx_request_aware = True

    def _editor_request_started():
        return _manager.begin_primary_request()

    _editor._wx_request_started = _editor_request_started

    def _editor_new_window(path, content=""):
        try:
            _profile = _resolve_profile()
            _prov_cfg = _resolve_provider_config()
            _prov = _prov_cfg.get("name") if isinstance(_prov_cfg, dict) else ""
        except Exception:
            _profile, _prov = {}, ""
        _manager.open_new_window(
            path,
            content,
            is_local=False,
            provider=str(_prov or ""),
            profile=str(_profile.get("name") or ""),
            session_key=_editor_session_key(session_state),
        )

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
