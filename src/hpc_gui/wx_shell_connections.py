"""wx shell connections workflows."""
from __future__ import annotations

from pathlib import Path
from hpc_gui.wx_shell_file_transfer import _cancel_transfer_sessions
from hpc_gui.wx_shell_files import _remote_files_callbacks


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
            lifecycle.register_cleanup(ssh.close, worker_safe=True)
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
        # W24 DIR-SESSION-001 / SESSION-REBIND-001: rebind directories storage
        # roots from the CURRENT session after connect.
        try:
            dirs_panel = session_state.get("_embedded_directories_panel")
            if dirs_panel is not None and hasattr(dirs_panel, "_wx_dirs_rebind"):
                dirs_panel._wx_dirs_rebind(session_state)
        except Exception:
            pass
        # W55 A1 (HPC-W10-GJ2-030): the shell status bar is the canonical
        # connection indicator; reflect the new session immediately.
        _update_shell_status_text(parent, session_state)

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
        # W24 SESSION-DISCONNECT-001 / DIR-009: explicit disconnected state,
        # never a stale listing or placeholder root presented as valid.
        try:
            dirs_panel = session_state.get("_embedded_directories_panel")
            if dirs_panel is not None and hasattr(dirs_panel, "_wx_dirs_disconnected"):
                dirs_panel._wx_dirs_disconnected()
        except Exception:
            pass
        # W25 XFER-013: invalidate in-flight remote transfers predictably on
        # disconnect instead of leaving them parked on a dead transport.
        _cancel_transfer_sessions(session_state)
        # W55 A1 (HPC-W10-GJ2-030): drop the stale profile from the shell
        # status bar the moment the session is gone.
        _update_shell_status_text(parent, session_state)

    return {"profiles": profiles, "lifecycle": lifecycle, "on_connected": on_connected, "on_disconnected": on_disconnected}
